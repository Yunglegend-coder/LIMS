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
        editable=False,
    )

    sample_type = models.CharField(
        max_length=30,
        choices=SampleType.choices,
    )

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

    history = models.TextField(
        blank=True,
    )

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

    antibiotics_used = models.TextField(
        blank=True,
    )

    mortality_pattern = models.TextField(
        blank=True,
    )

    pathology = models.TextField(
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

        if self.house and self.house.farm != self.farm:
            raise ValidationError(
                {
                    "house": "The selected house does not belong to the selected farm."
                }
            )

    def __str__(self):
        return self.case_code