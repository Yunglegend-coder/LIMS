from django.db import models
from django.core.exceptions import ValidationError
from samples.models import SampleType, DocSubtype, Sample




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

    is_biochemical = models.BooleanField(
        default=False,
        help_text="Exclude biochemical identification tests from customer PDF/DOCX reports.",
    )

    is_client_visible = models.BooleanField(
        default=True,
        help_text="Show completed results for this assay in client-facing reports.",
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

    doc_subtype = models.CharField(
        max_length=30,
        choices=DocSubtype.choices,
        blank=True,
        help_text="Set this only for a DOC subtype specific assay mapping.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("sample_type", "doc_subtype", "assay"),
                name="unique_sample_type_subtype_assay",
            ),
        ]
        ordering = ["sample_type", "assay__name"]

    def clean(self):
        super().clean()
        if self.sample_type != SampleType.DOC and self.doc_subtype:
            raise ValidationError({"doc_subtype": "DOC subtype can only be set for DOC mappings."})

    def __str__(self):
        label = self.get_sample_type_display()
        if self.doc_subtype:
            label = dict(DocSubtype.choices).get(self.doc_subtype, self.doc_subtype)
        return f"{label} → {self.assay.name}"


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

    doc_subtype = models.CharField(
        max_length=30,
        choices=DocSubtype.choices,
        blank=True,
        help_text="Identifies which DOC material this assay order is for.",
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
                fields=["sample", "assay", "doc_subtype"],
                name="unique_sample_assay_subtype",
            )
        ]

    def clean(self):
        super().clean()
        if self.sample_id and self.sample.sample_type != SampleType.DOC and self.doc_subtype:
            raise ValidationError({"doc_subtype": "DOC subtype can only be set for DOC assay orders."})

    def __str__(self):
        subtype = f" - {self.get_doc_subtype_display()}" if self.doc_subtype else ""
        return f"{self.sample.case_code} - {self.assay.name}{subtype}"
