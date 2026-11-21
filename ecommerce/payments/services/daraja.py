import base64
import hashlib
import re
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache
from django.utils import timezone
from requests.auth import HTTPBasicAuth

from ecommerce.payments.credentials import (
    PaymentConfigurationError,
    load_mpesa_credentials,
)


class DarajaError(Exception):
    """A safe, user-displayable Daraja integration error."""


class DarajaOutcomeUnknown(DarajaError):
    """The STK request may have reached Safaricom but its response was lost."""


def _base_url(environment):
    if environment == "sandbox":
        return "https://sandbox.safaricom.co.ke"
    return "https://api.safaricom.co.ke"


def _validate_callback_url(callback_url):
    parsed = urlparse(callback_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise PaymentConfigurationError(
            "MPESA_CALLBACK_URL must be a public HTTPS URL."
        )


def _callback_url(credentials):
    _validate_callback_url(credentials.callback_url)
    return credentials.callback_url


def get_access_token():
    credentials = load_mpesa_credentials()
    _callback_url(credentials)
    cache_suffix = hashlib.sha256(credentials.consumer_key.encode()).hexdigest()[:12]
    cache_key = f"daraja-access-token:{credentials.environment}:{cache_suffix}"
    token = cache.get(cache_key)
    if token:
        return token

    try:
        response = requests.get(
            f"{_base_url(credentials.environment)}/oauth/v1/generate",
            params={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(credentials.consumer_key, credentials.consumer_secret),
            timeout=(5, 15),
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise DarajaError("Could not authenticate with Safaricom Daraja.") from exc

    if not isinstance(data, dict):
        raise DarajaError("Safaricom returned an invalid authentication response.")
    token = data.get("access_token")
    if not token:
        raise DarajaError("Safaricom did not return an access token.")
    try:
        expires_in = int(data.get("expires_in", 3600))
    except (TypeError, ValueError):
        expires_in = 3600
    cache.set(cache_key, token, timeout=max(30, expires_in - 60))
    return token


def normalize_kenyan_phone(phone_number):
    digits = re.sub(r"\D", "", str(phone_number or ""))
    if len(digits) == 10 and digits.startswith(("07", "01")):
        digits = "254" + digits[1:]
    elif len(digits) == 12 and digits.startswith("254"):
        pass
    else:
        raise DarajaError("Enter a valid Kenyan mobile number, such as 0712345678.")
    if not re.fullmatch(r"254[17]\d{8}", digits):
        raise DarajaError("Enter a valid Kenyan mobile number, such as 0712345678.")
    return digits


def _stk_password(shortcode, passkey):
    timestamp = datetime.now(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")
    raw_password = f"{shortcode}{passkey}{timestamp}".encode("utf-8")
    password = base64.b64encode(raw_password).decode("ascii")
    return timestamp, password


def start_stk_push(payment, phone_number):
    credentials = load_mpesa_credentials()
    callback_url = _callback_url(credentials)
    if payment.currency != "KES":
        raise DarajaError("M-Pesa payments must use KES.")
    if payment.amount <= 0 or payment.amount != payment.amount.to_integral_value():
        raise DarajaError(
            "This order total includes cents. M-Pesa checkout needs a whole-KSh total; "
            "adjust the product prices before trying this payment."
        )

    phone = normalize_kenyan_phone(phone_number)
    timestamp, password = _stk_password(credentials.shortcode, credentials.passkey)
    amount = int(Decimal(payment.amount))
    order_ref = f"UP{payment.order_id}"[:12]
    payload = {
        "BusinessShortCode": credentials.shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": credentials.transaction_type,
        "Amount": amount,
        "PartyA": phone,
        "PartyB": credentials.shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": order_ref,
        "TransactionDesc": f"Upsteps order {payment.order_id}"[:20],
    }

    try:
        response = requests.post(
            f"{_base_url(credentials.environment)}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": f"Bearer {get_access_token()}"},
            timeout=(5, 25),
        )
    except requests.RequestException as exc:
        raise DarajaOutcomeUnknown(
            "We could not confirm whether Safaricom received the request. "
            "Check your phone before retrying."
        ) from exc
    if response.status_code >= 500:
        raise DarajaOutcomeUnknown(
            "Safaricom could not confirm whether it received the request. Check your phone before retrying."
        )
    if response.status_code >= 400:
        raise DarajaError("Safaricom rejected the M-Pesa request. Check the phone number and try again.")
    try:
        data = response.json()
    except ValueError as exc:
        raise DarajaOutcomeUnknown(
            "We could not read Safaricom's response. Check your phone before retrying."
        ) from exc

    if not isinstance(data, dict):
        raise DarajaError("Safaricom returned an invalid payment response.")
    if data.get("ResponseCode") != "0":
        raise DarajaError("Safaricom did not accept the M-Pesa request. Check the number and try again.")
    if not data.get("CheckoutRequestID"):
        raise DarajaOutcomeUnknown(
            "Safaricom accepted the request without returning a tracking reference. Check your phone before retrying."
        )
    return data, phone


def query_stk_push(payment):
    credentials = load_mpesa_credentials()
    if not payment.provider_reference:
        raise DarajaError("This payment has no Safaricom checkout reference to query.")
    timestamp, password = _stk_password(credentials.shortcode, credentials.passkey)
    payload = {
        "BusinessShortCode": credentials.shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": payment.provider_reference,
    }
    try:
        response = requests.post(
            f"{_base_url(credentials.environment)}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={"Authorization": f"Bearer {get_access_token()}"},
            timeout=(5, 25),
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise DarajaError("Could not query the M-Pesa payment status.") from exc
    if not isinstance(data, dict):
        raise DarajaError("Safaricom returned an invalid payment-status response.")
    return data
