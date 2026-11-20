from dataclasses import dataclass

from django.conf import settings


class PaymentConfigurationError(Exception):
    """Raised when Daraja settings are missing or invalid."""


@dataclass(frozen=True)
class MpesaCredentials:
    environment: str
    consumer_key: str
    consumer_secret: str
    shortcode: str
    passkey: str
    callback_url: str
    callback_token: str
    transaction_type: str


def load_mpesa_credentials():
    environment = settings.MPESA_ENVIRONMENT
    if environment not in {"sandbox", "production"}:
        raise PaymentConfigurationError("MPESA_ENVIRONMENT must be sandbox or production.")

    values = {
        "MPESA_CONSUMER_KEY": settings.MPESA_CONSUMER_KEY,
        "MPESA_CONSUMER_SECRET": settings.MPESA_CONSUMER_SECRET,
        "MPESA_SHORTCODE": settings.MPESA_SHORTCODE,
        "MPESA_PASSKEY": settings.MPESA_PASSKEY,
        "MPESA_CALLBACK_URL": settings.MPESA_CALLBACK_URL,
        "MPESA_CALLBACK_TOKEN": settings.MPESA_CALLBACK_TOKEN,
    }
    missing = [name for name, value in values.items() if not value.strip()]
    if missing:
        raise PaymentConfigurationError(
            "Missing Daraja settings: " + ", ".join(missing)
        )
    if len(values["MPESA_CALLBACK_TOKEN"]) < 32:
        raise PaymentConfigurationError("MPESA_CALLBACK_TOKEN must be at least 32 characters.")

    return MpesaCredentials(
        environment=environment,
        consumer_key=values["MPESA_CONSUMER_KEY"],
        consumer_secret=values["MPESA_CONSUMER_SECRET"],
        shortcode=values["MPESA_SHORTCODE"],
        passkey=values["MPESA_PASSKEY"],
        callback_url=values["MPESA_CALLBACK_URL"].rstrip("/"),
        callback_token=values["MPESA_CALLBACK_TOKEN"],
        transaction_type=settings.MPESA_TRANSACTION_TYPE,
    )
