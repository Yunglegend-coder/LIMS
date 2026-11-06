from unittest.mock import patch
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from customers.models import Customer
from locations.models import Farm
from samples.choices import SampleType
from samples.models import Sample
from samples.services import RegisterSampleService

from .models import UserNotification, UserRole
from .messaging import send_whatsapp_text


class AuthenticationAndRoleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="frontdesk",
            password="secure-password",
        )

    def test_unauthenticated_user_is_redirected_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

    def test_login_and_logout(self):
        response = self.client.post(
            reverse("login"),
            {"username": "frontdesk", "password": "secure-password"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertRedirects(
            self.client.get(reverse("dashboard")),
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

    def test_role_can_be_changed_and_controls_sample_registration(self):
        self.user.profile.role = UserRole.VET_DOCTOR
        self.user.profile.save(update_fields=["role"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("sample_create"))
        self.assertEqual(response.status_code, 403)

    def test_admin_creates_user_and_updates_signal_created_profile(self):
        admin_user = get_user_model().objects.create_superuser(
            username="site-admin",
            password="admin-password",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "new-scientist",
                "usable_password": "true",
                "password1": "scientist-password-123",
                "password2": "scientist-password-123",
                "profile-TOTAL_FORMS": "1",
                "profile-INITIAL_FORMS": "0",
                "profile-MIN_NUM_FORMS": "0",
                "profile-MAX_NUM_FORMS": "1",
                "profile-0-role": UserRole.LAB_SCIENTIST,
                "profile-0-whatsapp": "+2348012345678",
                "profile-0-id": "",
                "profile-0-user": "",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        created_user = get_user_model().objects.get(username="new-scientist")
        self.assertEqual(created_user.profile.role, UserRole.LAB_SCIENTIST)
        self.assertEqual(created_user.profile.whatsapp, "+2348012345678")


class SampleNotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.doctor = User.objects.create_user(
            username="vet", email="vet@example.com"
        )
        self.doctor.profile.role = UserRole.VET_DOCTOR
        self.doctor.profile.whatsapp = "+2348000000001"
        self.doctor.profile.save()

        self.scientist = User.objects.create_user(
            username="scientist", email="lab@example.com"
        )
        self.scientist.profile.role = UserRole.LAB_SCIENTIST
        self.scientist.profile.whatsapp = "+2348000000002"
        self.scientist.profile.save()

        self.receptionist = User.objects.create_user(username="reception")
        customer = Customer.objects.create(
            name="Farm Client",
            whatsapp="+2348000000010",
            state="Kaduna",
        )
        farm = Farm.objects.create(customer=customer, name="Farm A")
        self.sample = Sample.objects.create(
            registered_by=self.receptionist,
            farm=farm,
            case_code="KD-TEST-NOTIFY",
            sample_type=SampleType.CARCASS,
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="smtp.test",
        EMAIL_HOST_USER="lims@example.test",
        EMAIL_HOST_PASSWORD="test-password",
        DEFAULT_FROM_EMAIL="LIMS <lims@example.test>",
    )
    @patch("accounts.messaging.send_whatsapp_text", return_value=(True, "sent"))
    @patch("accounts.messaging.send_mass_mail")
    def test_new_sample_notifies_doctors_and_scientists(self, send_email, send_whatsapp):
        form = Mock()
        form.save.return_value = Sample(
            farm=self.sample.farm,
            sample_type=SampleType.CARCASS,
        )
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            registered_sample = RegisterSampleService.execute(
                form=form,
                user=self.receptionist,
            )

        self.assertEqual(
            UserNotification.objects.filter(sample=registered_sample).count(),
            2,
        )
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(send_email.call_count, 1)
        self.assertEqual(len(send_email.call_args.args[0]), 2)
        self.assertEqual(send_whatsapp.call_count, 2)
        self.assertEqual(
            set(UserNotification.objects.filter(sample=registered_sample).values_list("recipient__username", flat=True)),
            {"vet", "scientist"},
        )


class WhatsAppClientTests(TestCase):
    @override_settings(
        WHATSAPP_ACCESS_TOKEN="test-token",
        WHATSAPP_PHONE_NUMBER_ID="12345",
        WHATSAPP_API_VERSION="v26.0",
        WHATSAPP_TEMPLATE_NAME="sample_alert",
        WHATSAPP_TEMPLATE_LANGUAGE="en_US",
    )
    @patch("accounts.messaging.urlopen")
    def test_cloud_api_template_message_uses_normalized_number(self, urlopen):
        urlopen.return_value.__enter__.return_value.status = 200

        sent, _ = send_whatsapp_text("+234 801-234-5678", "Sample KD-1 ready")

        self.assertTrue(sent)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://graph.facebook.com/v26.0/12345/messages")
        import json
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["to"], "2348012345678")
        self.assertEqual(payload["template"]["name"], "sample_alert")
        self.assertEqual(
            payload["template"]["components"][0]["parameters"][0]["text"],
            "Sample KD-1 ready",
        )

    @override_settings(WHATSAPP_ACCESS_TOKEN="", WHATSAPP_PHONE_NUMBER_ID="")
    def test_whatsapp_reports_unconfigured_provider_without_network_call(self):
        sent, message = send_whatsapp_text("+2348012345678", "test")
        self.assertFalse(sent)
        self.assertIn("WHATSAPP_ACCESS_TOKEN", message)
