import json
import logging
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mass_mail

from .models import UserNotification, UserProfile, UserRole

logger = logging.getLogger(__name__)


def email_delivery_status():
    backend = settings.EMAIL_BACKEND
    if backend == "django.core.mail.backends.console.EmailBackend":
        return False, (
            "Email is in console-only mode. Configure SMTP using EMAIL_BACKEND, "
            "EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, "
            "and a real DEFAULT_FROM_EMAIL."
        )
    if backend.endswith("smtp.EmailBackend") and not settings.EMAIL_HOST:
        return False, "EMAIL_HOST is missing from the SMTP configuration."
    if backend.endswith("smtp.EmailBackend") and (
        not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD
    ):
        return False, (
            "Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD. For Gmail, use your Gmail "
            "address and a Google App Password."
        )
    if not settings.DEFAULT_FROM_EMAIL or "localhost" in settings.DEFAULT_FROM_EMAIL.lower():
        return False, "Set DEFAULT_FROM_EMAIL to a real address before sending email."
    return True, "Email delivery is configured."


def whatsapp_delivery_status(recipient=""):
    missing = []
    if not settings.WHATSAPP_ACCESS_TOKEN:
        missing.append("WHATSAPP_ACCESS_TOKEN")
    if not settings.WHATSAPP_PHONE_NUMBER_ID:
        missing.append("WHATSAPP_PHONE_NUMBER_ID")
    if not settings.WHATSAPP_TEMPLATE_NAME:
        missing.append("WHATSAPP_TEMPLATE_NAME (approved template)")
    if not recipient:
        return False, "The recipient has no WhatsApp number saved."
    if missing:
        return False, "Configure " + ", ".join(missing) + " to enable WhatsApp delivery."
    return True, "WhatsApp delivery is configured."


def send_whatsapp_text(recipient, text):
    """Send a WhatsApp Cloud API text message when credentials are configured."""
    ready, detail = whatsapp_delivery_status(recipient)
    if not ready:
        return False, detail

    token = settings.WHATSAPP_ACCESS_TOKEN
    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID

    recipient = re.sub(r"\D", "", recipient)
    if recipient.startswith("00"):
        recipient = recipient[2:]

    version = getattr(settings, "WHATSAPP_API_VERSION", "v23.0")
    url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
    }
    payload.update({
        "type": "template",
        "template": {
            "name": settings.WHATSAPP_TEMPLATE_NAME,
            "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUAGE},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": text[:1024]}],
            }],
        },
    })
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            if 200 <= response.status < 300:
                return True, "WhatsApp message sent."
            return False, "WhatsApp provider rejected the message."
    except (HTTPError, URLError, TimeoutError) as error:
        logger.warning("WhatsApp delivery failed: %s", error)
        return False, "WhatsApp delivery failed. Check provider settings and recipient number."


def notify_staff_of_new_sample(sample):
    roles = (UserRole.VET_DOCTOR, UserRole.LAB_SCIENTIST)
    profiles = list(
        UserProfile.objects.filter(
            role__in=roles,
            user__is_active=True,
        ).select_related("user")
    )
    if not profiles:
        return

    customer_name = sample.farm.customer.name
    title = f"New sample registered: {sample.case_code}"
    message = f"{sample.case_code} from {customer_name} is ready for laboratory processing."
    UserNotification.objects.bulk_create([
        UserNotification(
            recipient=profile.user,
            sample=sample,
            title=title,
            message=message,
        )
        for profile in profiles
    ])

    email_ready, email_status = email_delivery_status()
    email_messages = [
        (
            title,
            f"{message}\n\nOpen the sample in Poultry LIMS: "
            f"{getattr(settings, 'SITE_BASE_URL', '').rstrip('/')}/samples/{sample.pk}/",
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
        )
        for profile in profiles
        if profile.user.email
    ]
    if email_messages and email_ready:
        try:
            send_mass_mail(email_messages, fail_silently=False)
        except Exception:
            logger.exception("Unable to send new-sample email notifications")
    elif email_messages:
        logger.info("New-sample email notification skipped: %s", email_status)

    for profile in profiles:
        if profile.whatsapp:
            sent, detail = send_whatsapp_text(profile.whatsapp, message)
            if not sent:
                logger.info("Sample WhatsApp alert was not delivered: %s", detail)
