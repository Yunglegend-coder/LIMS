from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from assays.models import AssayOrder, AssayStatus, AssayType, LaboratorySection
from customers.models import Customer
from accounts.models import UserRole
from locations.models import Farm
from results.models import (
    AssayResult,
    BinaryChoice,
    BinaryResult,
    CultureGrowthChoice,
    CultureResult,
    SampleReport,
)
from results.reporting import build_report_data
from samples.choices import SampleStatus, SampleType
from samples.models import Sample


class ResultsWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="lab-user",
            password="test-password",
        )
        cls.user.profile.role = UserRole.MANAGER
        cls.user.profile.save(update_fields=["role"])
        customer = Customer.objects.create(
            name="Example Poultry",
            email="client@example.com",
            whatsapp="08000000000",
            state="Lagos",
        )
        farm = Farm.objects.create(customer=customer, name="Example Farm")
        cls.sample = Sample.objects.create(
            registered_by=cls.user,
            farm=farm,
            case_code="KD-TEST-001",
            sample_type=SampleType.CARCASS,
            status=SampleStatus.COMPLETED,
        )
        assay = AssayType.objects.create(
            name="Salmonella screen",
            category="BINARY",
            laboratory_section=LaboratorySection.MICROBIOLOGY,
        )
        cls.order = AssayOrder.objects.create(
            sample=cls.sample,
            assay=assay,
            status=AssayStatus.COMPLETED,
        )
        cls.assay_result = AssayResult.objects.create(
            assay_order=cls.order,
            performed_by=cls.user,
            remarks="Initial observation",
        )
        BinaryResult.objects.create(
            assay_result=cls.assay_result,
            result=BinaryChoice.POSITIVE,
        )
        cls.culture_assay = AssayType.objects.create(
            name="Fungal culture",
            category="CULTURE",
            laboratory_section=LaboratorySection.MICROBIOLOGY,
        )
        cls.culture_order = AssayOrder.objects.create(
            sample=cls.sample,
            assay=cls.culture_assay,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_completed_list_shows_completed_sample_and_report_link(self):
        response = self.client.get(
            reverse(
                "completed_results",
                kwargs={"laboratory": LaboratorySection.MICROBIOLOGY},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.sample.case_code)
        self.assertContains(
            response,
            reverse("sample_final_result", kwargs={"pk": self.sample.pk}),
        )
        self.assertNotContains(response, 'title="Edit result"')
        self.assertNotContains(response, 'title="Print result"')

    def test_final_report_displays_saved_result_and_metadata(self):
        response = self.client.get(
            reverse("sample_final_result", kwargs={"pk": self.sample.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.sample.case_code)
        self.assertContains(response, "<strong>Result:</strong> +")
        self.assertContains(response, "Initial observation")
        self.assertContains(response, "Salmonella screen")

    def test_edit_updates_existing_result_and_returns_to_report(self):
        response = self.client.post(
            reverse(
                "assay_result_edit",
                kwargs={"pk": self.assay_result.pk},
            ),
            {"result": BinaryChoice.NEGATIVE, "remarks": "Updated finding"},
        )

        self.assertRedirects(
            response,
            reverse("sample_final_result", kwargs={"pk": self.sample.pk}),
        )
        self.assay_result.refresh_from_db()
        self.assay_result.binary_result.refresh_from_db()
        self.assertEqual(self.assay_result.binary_result.result, BinaryChoice.NEGATIVE)
        self.assertEqual(self.assay_result.remarks, "Updated finding")

    def test_individual_culture_post_saves_result_without_missing_assay_attribute(self):
        response = self.client.post(
            reverse("assay_result_create", kwargs={"pk": self.culture_order.pk}),
            {
                "growth": CultureGrowthChoice.NO_GROWTH,
                "organism_name": "Aspergillus niger",
                "colony_description": "",
                "identification_notes": "",
                "remarks": "No fungal growth detected",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "pending_results",
                kwargs={"laboratory": LaboratorySection.MICROBIOLOGY},
            ),
        )
        self.culture_order.refresh_from_db()
        self.assertEqual(self.culture_order.status, AssayStatus.COMPLETED)
        result = CultureResult.objects.get(
            assay_result__assay_order=self.culture_order
        )
        self.assertEqual(result.growth, CultureGrowthChoice.NO_GROWTH)
        self.assertEqual(result.organism_name, "Aspergillus niger")

    def test_pending_culture_bulk_entry_saves_results_and_completes_order(self):
        url = reverse(
            "pending_assay_results",
            kwargs={
                "laboratory": LaboratorySection.MICROBIOLOGY,
                "assay_pk": self.culture_assay.pk,
            },
        )
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(
            page,
            f'name="culture_{self.culture_order.pk}_growth"',
        )

        response = self.client.post(
            url,
            {
                f"culture_{self.culture_order.pk}_growth": CultureGrowthChoice.GROWTH,
                f"culture_{self.culture_order.pk}_organism_name": "Aspergillus niger",
                f"culture_{self.culture_order.pk}_colony_description": "Black conidia",
                f"culture_{self.culture_order.pk}_identification_notes": "Microscopy confirmed",
                f"culture_{self.culture_order.pk}_remarks": "Fungal growth present",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "pending_assay_results",
                kwargs={
                    "laboratory": LaboratorySection.MICROBIOLOGY,
                    "assay_pk": self.culture_assay.pk,
                },
            ),
        )
        self.culture_order.refresh_from_db()
        self.assertEqual(self.culture_order.status, AssayStatus.COMPLETED)
        result = CultureResult.objects.get(
            assay_result__assay_order=self.culture_order
        )
        self.assertEqual(result.organism_name, "Aspergillus niger")
        self.assertEqual(result.colony_description, "Black conidia")
        self.assertEqual(
            result.assay_result.remarks,
            "Fungal growth present",
        )

    def test_report_narrative_saves_and_appears_in_downloads(self):
        report_url = reverse("sample_final_result", kwargs={"pk": self.sample.pk})
        response = self.client.post(
            report_url,
            {
                "clinical_diagnosis": "Systemic bacterial infection",
                "laboratory_diagnosis": "Citrobacter spp isolated",
                "isolate": "Citrobacter spp",
                "comments_recommendations": "Administer treatment for five days.",
            },
        )
        self.assertRedirects(response, report_url)

        report = SampleReport.objects.get(sample=self.sample)
        self.assertEqual(report.updated_by, self.user)
        self.assertContains(
            self.client.get(report_url),
            "Administer treatment for five days.",
        )

        data = build_report_data(self.sample, report)
        self.assertEqual(data["lab_name"], "KADUNA POULTRY DISEASE DIAGNOSTIC LABORATORY")
        self.assertEqual(data["clinical_diagnosis"], "Systemic bacterial infection")
        self.assertEqual(data["comments"], "Administer treatment for five days.")

    def test_report_downloads_return_pdf_and_docx_files(self):
        pdf_response = self.client.get(
            reverse("sample_report_pdf", kwargs={"pk": self.sample.pk})
        )
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))

        docx_response = self.client.get(
            reverse("sample_report_docx", kwargs={"pk": self.sample.pk})
        )
        self.assertEqual(docx_response.status_code, 200)
        self.assertEqual(
            docx_response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        from io import BytesIO
        from zipfile import ZipFile
        import xml.etree.ElementTree as ET

        with ZipFile(BytesIO(docx_response.content)) as document:
            root = ET.fromstring(document.read("word/document.xml"))
        word_text = " ".join(root.itertext())
        self.assertIn("KADUNA POULTRY DISEASE DIAGNOSTIC LABORATORY", word_text)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="smtp.test",
        EMAIL_HOST_USER="lims@example.test",
        EMAIL_HOST_PASSWORD="test-password",
        DEFAULT_FROM_EMAIL="LIMS <lims@example.test>",
    )
    @patch("results.views.EmailMessage")
    def test_report_email_action_attaches_pdf(self, email_message):
        response = self.client.post(
            reverse(
                "sample_report_send",
                kwargs={"pk": self.sample.pk, "channel": "email"},
            )
        )

        self.assertRedirects(
            response,
            reverse("sample_final_result", kwargs={"pk": self.sample.pk}),
        )
        email_message.assert_called_once()
        email_message.return_value.attach.assert_called_once()
        self.assertEqual(
            email_message.return_value.attach.call_args.args[2],
            "application/pdf",
        )

    @patch("results.views.EmailMessage")
    def test_report_email_does_not_claim_delivery_in_console_mode(self, email_message):
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        ):
            response = self.client.post(
                reverse(
                    "sample_report_send",
                    kwargs={"pk": self.sample.pk, "channel": "email"},
                ),
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "console-only mode")
        email_message.assert_not_called()

    @patch("results.views.send_whatsapp_text", return_value=(True, "sent"))
    def test_report_whatsapp_action_sends_result_summary(self, send_whatsapp):
        response = self.client.post(
            reverse(
                "sample_report_send",
                kwargs={"pk": self.sample.pk, "channel": "whatsapp"},
            )
        )

        self.assertRedirects(
            response,
            reverse("sample_final_result", kwargs={"pk": self.sample.pk}),
        )
        send_whatsapp.assert_called_once()
        self.assertIn(self.sample.case_code, send_whatsapp.call_args.args[1])
