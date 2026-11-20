import json
import secrets
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ecommerce.ui.models import Order
from .credentials import PaymentConfigurationError
from .models import Payment, PaymentEvent
from .services.daraja import (
    DarajaError,
    DarajaOutcomeUnknown,
    query_stk_push,
    start_stk_push,
)


def _json_body(request):
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _owned_order(request, order_number):
    orders = Order.objects.filter(order_number=order_number)
    if request.user.is_authenticated:
        orders = orders.filter(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            raise Http404("Order not found.")
        orders = orders.filter(session_key=session_key)
    order = orders.first()
    if not order:
        raise Http404("Order not found.")
    return order


def _owned_payment(request, reference):
    payments = Payment.objects.select_related("order").filter(reference=reference)
    if request.user.is_authenticated:
        payments = payments.filter(order__user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            raise Http404("Payment not found.")
        payments = payments.filter(order__session_key=session_key)
    payment = payments.first()
    if not payment:
        raise Http404("Payment not found.")
    return payment


def _payment_json(payment):
    return {
        "reference": str(payment.reference),
        "status": payment.status,
        "status_display": payment.get_status_display(),
        "order_status": payment.order.status,
        "receipt_number": payment.metadata.get("receipt_number", ""),
    }


def _reconcile_if_due(payment):
    if (
        payment.status != Payment.Status.PROCESSING
        or not payment.provider_reference
        or timezone.now() - payment.updated_at < timedelta(seconds=30)
    ):
        return payment

    try:
        response = query_stk_push(payment)
        result_code = str(response.get("ResultCode", ""))
        result_description = str(response.get("ResultDesc", ""))[:250]
        query_error = ""
    except DarajaError as exc:
        result_code = ""
        result_description = ""
        query_error = str(exc)

    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("order").get(pk=payment.pk)
        if payment.status != Payment.Status.PROCESSING:
            return payment
        now = timezone.now()
        metadata = {**payment.metadata, "last_status_query_at": now.isoformat()}
        if query_error:
            metadata["last_status_query_error"] = query_error
        else:
            metadata.pop("last_status_query_error", None)
        event_data = {"result_code": result_code, "result_description": result_description}

        if result_code == "0":
            payment.status = Payment.Status.SUCCEEDED
            payment.completed_at = now
            payment.order.status = Order.Status.CONFIRMED
            payment.order.save(update_fields=["status", "updated_at"])
        elif result_code:
            payment.status = Payment.Status.CANCELLED if result_code == "1032" else Payment.Status.FAILED
            payment.completed_at = now

        payment.metadata = metadata
        payment.save(update_fields=["status", "completed_at", "metadata", "updated_at"])
        if not query_error:
            PaymentEvent.objects.create(
                payment=payment,
                event_type="stk_status_query",
                data=event_data,
                processed_at=now if result_code else None,
            )
    return payment


@require_POST
def start_stk_push_view(request):
    payload = _json_body(request)
    if not payload or not payload.get("order_number"):
        return JsonResponse({"error": "A valid order number is required."}, status=400)
    try:
        order = _owned_order(request, payload["order_number"])
    except (Http404, ValueError):
        return JsonResponse({"error": "That order could not be found."}, status=404)
    if order.payment_method != Order.PaymentMethod.MPESA:
        return JsonResponse({"error": "This order was not placed with M-Pesa selected."}, status=400)
    if order.status != Order.Status.PENDING:
        return JsonResponse({"error": "This order is no longer awaiting payment."}, status=409)

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        existing = locked_order.payments.filter(method=Payment.Method.MPESA).first()
        if existing and existing.status == Payment.Status.SUCCEEDED:
            return JsonResponse(_payment_json(existing))
        if existing and existing.status in {Payment.Status.PENDING, Payment.Status.PROCESSING}:
            return JsonResponse({
                **_payment_json(existing),
                "message": "A payment request is already pending. Check your phone before retrying.",
            }, status=409)
        payment = Payment.objects.create(
            order=locked_order,
            method=Payment.Method.MPESA,
            provider=Payment.Provider.MPESA,
            amount=locked_order.total,
            currency=locked_order.currency,
            status=Payment.Status.PENDING,
        )

    try:
        response_data, normalized_phone = start_stk_push(payment, order.customer_phone)
    except DarajaOutcomeUnknown as exc:
        payment.metadata = {"initiation_state": "unknown"}
        payment.save(update_fields=["metadata", "updated_at"])
        PaymentEvent.objects.create(
            payment=payment,
            event_type="stk_push_outcome_unknown",
            data={"reason": str(exc)},
        )
        return JsonResponse({
            "error": str(exc), "payment": _payment_json(payment),
        }, status=502)
    except (DarajaError, PaymentConfigurationError) as exc:
        payment.status = Payment.Status.FAILED
        payment.completed_at = timezone.now()
        payment.metadata = {"initiation_state": "rejected"}
        payment.save(update_fields=["status", "completed_at", "metadata", "updated_at"])
        PaymentEvent.objects.create(
            payment=payment,
            event_type="stk_push_initiation_failed",
            data={"reason": str(exc)},
        )
        return JsonResponse({
            "error": str(exc), "payment": _payment_json(payment),
        }, status=502)

    payment.status = Payment.Status.PROCESSING
    payment.provider_reference = response_data["CheckoutRequestID"]
    payment.metadata = {
        "merchant_request_id": response_data.get("MerchantRequestID", ""),
        "checkout_request_id": response_data["CheckoutRequestID"],
        "phone_number": normalized_phone,
        "customer_message": response_data.get("CustomerMessage", ""),
    }
    payment.save(update_fields=["status", "provider_reference", "metadata", "updated_at"])
    PaymentEvent.objects.create(
        payment=payment,
        event_type="stk_push_initiated",
        data={
            "merchant_request_id": response_data.get("MerchantRequestID", ""),
            "checkout_request_id": response_data["CheckoutRequestID"],
        },
    )
    return JsonResponse({
        **_payment_json(payment),
        "message": "M-Pesa prompt sent. Check your phone and enter your PIN to approve it.",
    })


@require_GET
def payment_status(request, reference):
    try:
        payment = _owned_payment(request, reference)
    except Http404:
        raise
    payment = _reconcile_if_due(payment)
    return JsonResponse(_payment_json(payment))


@csrf_exempt
@require_POST
def stk_callback(request, token):
    configured_token = settings.MPESA_CALLBACK_TOKEN
    if not configured_token or not secrets.compare_digest(token, configured_token):
        return JsonResponse({"error": "Not found."}, status=404)
    payload = _json_body(request)
    callback = (payload or {}).get("Body", {}).get("stkCallback")
    if not isinstance(callback, dict):
        return JsonResponse({"error": "Invalid callback payload."}, status=400)
    checkout_id = callback.get("CheckoutRequestID")
    merchant_id = callback.get("MerchantRequestID")
    if not checkout_id or not merchant_id:
        return JsonResponse({"error": "Callback is missing transaction identifiers."}, status=400)
    if callback.get("ResultCode") is None:
        return JsonResponse({"error": "Callback is missing its result code."}, status=400)

    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(
            provider=Payment.Provider.MPESA,
            provider_reference=checkout_id,
        ).select_related("order").first()
        if not payment:
            return JsonResponse({"error": "Payment attempt not found."}, status=404)
        if payment.metadata.get("merchant_request_id") != merchant_id:
            return JsonResponse({"error": "Callback identifiers do not match."}, status=400)
        if PaymentEvent.objects.filter(provider_event_id=checkout_id).exists():
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Callback already processed."})

        result_code = str(callback.get("ResultCode", ""))
        event_data = {"result_code": result_code, "result_description": str(callback.get("ResultDesc", ""))[:250]}
        if result_code == "0":
            callback_items = (callback.get("CallbackMetadata") or {}).get("Item", [])
            details = {
                item.get("Name"): item.get("Value")
                for item in callback_items
                if isinstance(item, dict) and item.get("Name")
            }
            try:
                paid_amount = Decimal(str(details.get("Amount", "")))
                expected_phone = payment.metadata.get("phone_number", "")
                paid_phone = str(details.get("PhoneNumber", ""))
            except InvalidOperation:
                return JsonResponse({"error": "Invalid payment amount in callback."}, status=400)
            receipt = details.get("MpesaReceiptNumber")
            if paid_amount != payment.amount or not receipt or paid_phone != expected_phone:
                return JsonResponse({"error": "Payment callback details did not match the order."}, status=400)
            event_data.update({"amount": str(paid_amount), "receipt_number": str(receipt)})
            payment.metadata = {**payment.metadata, "receipt_number": str(receipt)}
            payment.status = Payment.Status.SUCCEEDED
            payment.completed_at = timezone.now()
            payment.order.status = Order.Status.CONFIRMED
            payment.order.save(update_fields=["status", "updated_at"])
        else:
            payment.status = Payment.Status.FAILED
            payment.completed_at = timezone.now()

        payment.save(update_fields=["status", "completed_at", "metadata", "updated_at"])
        PaymentEvent.objects.create(
            payment=payment,
            provider_event_id=checkout_id,
            event_type="stk_callback_success" if result_code == "0" else "stk_callback_failure",
            data=event_data,
            processed_at=timezone.now(),
        )
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted."})
