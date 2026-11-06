from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from core.models import LaboratorySite
from locations.models import Farm, House

from .choices import (
    Laboratory,
    Priority,
    SampleCondition,
    SampleStatus,
    SampleType,
    DocSubtype,
)


class Sample(models.Model):
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registered_samples",
    )

    farm = models.ForeignKey(
        Farm,
        on_delete=models.PROTECT,
        related_name="samples",
    )

    house = models.ForeignKey(
        House,
        on_delete=models.PROTECT,
        related_name="samples",
        null=True,
        blank=True,
    )

    site = models.ForeignKey(
        LaboratorySite,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    case_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
    )

    sample_type = models.CharField(
        max_length=30,
        choices=SampleType.choices,
    )

    doc_subtypes = models.JSONField(default=list, blank=True)

    laboratory = models.CharField(
        max_length=10,
        choices=Laboratory.choices,
        default=Laboratory.MICROBIOLOGY,
    )

    condition = models.CharField(
        max_length=20,
        choices=SampleCondition.choices,
        default=SampleCondition.GOOD,
    )

    collection_date = models.DateField(
        null=True,
        blank=True,
    )

    received_date = models.DateField(
        auto_now_add=True,
    )

    age = models.CharField(max_length=50, blank=True)

    breed_species = models.CharField(max_length=200, blank=True)

    population = models.PositiveIntegerField(null=True, blank=True)

    housing = models.CharField(max_length=200, blank=True)

    major_complaint = models.TextField(blank=True)

    source_of_birds = models.CharField(
        max_length=200,
        blank=True,
    )

    source_of_water = models.CharField(
        max_length=200,
        blank=True,
    )

    feed_type = models.CharField(
        max_length=200,
        blank=True,
    )

    last_vaccination = models.DateField(
        null=True,
        blank=True,
    )

    drugs = models.TextField(blank=True)

    medication = models.TextField(blank=True)

    vaccination_history = models.TextField(blank=True)

    vaccination = models.TextField(blank=True)

    mortality_pattern = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=SampleStatus.choices,
        default=SampleStatus.RECEIVED,
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    remarks = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-received_date", "-created_at"]

    def clean(self):
        super().clean()

        required_doc_subtypes = set(DocSubtype.values)
        if self.sample_type == SampleType.DOC and set(self.doc_subtypes or []) != required_doc_subtypes:
            raise ValidationError({"doc_subtypes": "Every DOC sample must include tissue, yolk sac, and intestine."})
        if self.sample_type != SampleType.DOC and self.doc_subtypes:
            raise ValidationError({"doc_subtypes": "DOC subtypes are only valid for DOC samples."})

        if self.house and self.house.farm != self.farm:
            raise ValidationError(
                {
                    "house": "The selected house does not belong to the selected farm."
                }
            )

    def get_assay_progress(self):
        """
        Return the number of completed assays and the total number
        of assays ordered for this sample.
        """

        total = self.assay_orders.count()

        completed = self.assay_orders.filter(
            status="COMPLETED"
        ).count()

        return completed, total

    def get_assay_progress_display(self):
        """
        Return a human-readable assay progress string.
        """

        completed, total = self.get_assay_progress()

        if total == 0:
            return "No assays ordered"

        return f"{completed}/{total} assays completed"

    def update_status_from_assays(self):
        """
        Update the overall sample status based on its assay orders.
        """

        total = self.assay_orders.count()

        completed = self.assay_orders.filter(
            status="COMPLETED"
        ).count()

        if total == 0:
            new_status = SampleStatus.RECEIVED

        elif completed == 0:
            new_status = SampleStatus.RECEIVED

        elif completed < total:
            new_status = SampleStatus.IN_PROGRESS

        else:
            new_status = SampleStatus.COMPLETED

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return self.case_code

    def get_sample_type_full_display(self):
        if self.sample_type == SampleType.DOC:
            labels = dict(DocSubtype.choices)
            subtype_labels = [
                labels.get(value, value).removeprefix("DOC/")
                for value in self.doc_subtypes or []
            ]
            if subtype_labels:
                return f"DOC ({', '.join(subtype_labels)})"
        return self.get_sample_type_display()
