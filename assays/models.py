from django.db import models
from samples.models import SampleType, Sample




class LaboratorySection(models.TextChoices):
    MICROBIOLOGY = "MICRO", "Microbiology"
    SEROLOGY = "SERO", "Serology"
    MOLECULAR = "MOLE", "Molecular Biology"

class AssayCategory(models.TextChoices):
    BINARY = "BINARY", "Binary"
    GRAM = "GRAM", "Gram Stain"
    CULTURE = "CULTURE", "Culture"
    AST = "AST", "Antibiotic Sensitivity Test"
    ELISA = "ELISA", "ELISA"
    PCR = "PCR", "PCR"
    COUNT = "COUNT", "Count"
    NDHI = "NDHI", "NDHI"
    TSI = "TSI", "TSI"



class AssayType(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    category = models.CharField(
        max_length=20,
        choices=AssayCategory.choices,
        default=AssayCategory.BINARY,
    )

    laboratory_section = models.CharField(
        max_length=10,
        choices=LaboratorySection.choices,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SampleTypeAssay(models.Model):

    sample_type = models.CharField(
        max_length=30,
        choices=SampleType.choices,
    )

    assay = models.ForeignKey(
        AssayType,
        on_delete=models.CASCADE,
        related_name="sample_types",
    )

    class Meta:
        unique_together = ("sample_type", "assay")
        ordering = ["sample_type", "assay__name"]

    def __str__(self):
        return f"{self.get_sample_type_display()} → {self.assay.name}"


class AssayStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    VERIFIED = "VERIFIED", "Verified"
    CANCELLED = "CANCELLED", "Cancelled"

class AssayOrder(models.Model):
    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name="assay_orders",
    )

    assay = models.ForeignKey(
        AssayType,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    status = models.CharField(
        max_length=20,
        choices=AssayStatus.choices,
        default=AssayStatus.PENDING,
    )

    requested_at = models.DateTimeField(auto_now_add=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    from django.conf import settings

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["sample", "assay"]
        constraints = [
            models.UniqueConstraint(
                fields=["sample", "assay"],
                name="unique_sample_assay",
            )
        ]

    def __str__(self):
        return f"{self.sample.case_code} - {self.assay.name}"