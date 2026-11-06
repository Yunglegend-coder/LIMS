from unittest.mock import patch

from django.test import TestCase, override_settings

# Create your tests here.
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import UserRole
from .models import Customer
from locations.models import Farm
from .models import CustomerEmailCampaign


class CustomerPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="customer-manager",
            password="test-password",
        )
        cls.user.profile.role = UserRole.MANAGER
        cls.user.profile.save(update_fields=["role"])
        cls.customer = Customer.objects.create(
            name="North Farm Client",
            email="client@example.com",
            whatsapp="08012345678",
            state="Kaduna",
        )
        cls.farm = Farm.objects.create(
            customer=cls.customer,
            name="T/Wada Poultry Farm",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_customer_list_renders_records_from_customer_app_template(self):
        response = self.client.get(reverse("customer_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "North Farm Client")
        self.assertContains(response, "T/Wada Poultry Farm")
        self.assertContains(response, reverse("customer_detail", kwargs={"pk": self.customer.pk}))

    def test_customer_search_matches_farm_name(self):
        response = self.client.get(
            reverse("customer_list"),
            {"search": "T/Wada"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "North Farm Client")

    def test_customer_detail_lists_related_farms(self):
        response = self.client.get(
            reverse("customer_detail", kwargs={"pk": self.customer.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "T/Wada Poultry Farm")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="smtp.test",
        EMAIL_HOST_USER="lims@example.test",
        EMAIL_HOST_PASSWORD="test-password",
        DEFAULT_FROM_EMAIL="LIMS <lims@example.test>",
    )
    @patch("customers.views.send_mass_mail")
    def test_batch_email_sends_individual_customer_messages(self, send_mass_mail):
        response = self.client.post(
            reverse("customer_email_campaign"),
            {
                "customers": [self.customer.pk],
                "subject": "Holiday hours",
                "body": "The laboratory will close on Friday.",
            },
        )

        self.assertRedirects(response, reverse("customer_list"))
        self.assertEqual(send_mass_mail.call_count, 1)
        messages = send_mass_mail.call_args.args[0]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0][3], [self.customer.email])
        self.assertEqual(CustomerEmailCampaign.objects.get().recipient_count, 1)

    def test_batch_email_page_explains_console_only_mode(self):
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        ):
            response = self.client.get(reverse("customer_email_campaign"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["email_delivery_ready"])
        self.assertContains(response, "console-only mode")
