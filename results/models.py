from django.conf import settings
from django.db import models

from assays.models import AssayOrder


class AssayResult(models.Model):
    assay_order = models.OneToOneField(
        AssayOrder,
        on_delete=models.CASCADE,
        related_name="result",
    )

    remarks = models.TextField(blank=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performed_results",
        null=True,
        blank=True,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="verified_results",
        null=True,
        blank=True,
    )

    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reported_at"]

    def __str__(self):
        return f"{self.assay_order.sample.case_code} - {self.assay_order.assay.name}"


class BinaryChoice(models.TextChoices):
    POSITIVE = "POS", "+"
    NEGATIVE = "NEG", "-"


class BinaryResult(models.Model):
    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="binary_result",
    )

    result = models.CharField(
        max_length=3,
        choices=BinaryChoice.choices,
    )

    def __str__(self):
        return self.get_result_display()

class GramStainChoice(models.TextChoices):
    GPC = "GPC", "Gram Positive Cocci"
    GPB = "GPB", "Gram Positive Bacilli"
    GNC = "GNC", "Gram Negative Cocci"
    GNB = "GNB", "Gram Negative Bacilli"
    MIXED = "MIX", "Mixed Flora"
    NONE = "NONE", "No Organisms Seen"


class GramStainResult(models.Model):
    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="gram_result",
    )

    result = models.CharField(
        max_length=10,
        choices=GramStainChoice.choices,
    )

class Antibiotic(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.code


class ASTInterpretation(models.TextChoices):
    SENSITIVE = "S", "Sensitive"
    INTERMEDIATE = "I", "Intermediate"
    RESISTANT = "R", "Resistant"


class ASTResult(models.Model):
    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="ast_result",
    )


class ASTResultItem(models.Model):
    ast_result = models.ForeignKey(
        ASTResult,
        on_delete=models.CASCADE,
        related_name="items",
    )

    antibiotic = models.ForeignKey(
        Antibiotic,
        on_delete=models.PROTECT,
    )

    interpretation = models.CharField(
        max_length=1,
        choices=ASTInterpretation.choices,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ast_result", "antibiotic"],
                name="unique_antibiotic_per_ast",
            )
        ]

class InstrumentInterpretation(models.TextChoices):
    POSITIVE = "POS", "Positive"
    NEGATIVE = "NEG", "Negative"
    SUSPECT = "SUS", "Suspect"


class InstrumentResult(models.Model):
    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="instrument_result",
    )

    optical_density = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    sp_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    titre = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    ct_value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    interpretation = models.CharField(
        max_length=10,
        choices=InstrumentInterpretation.choices,
        blank=True,
    )

class CountResult(models.Model):
    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="count_result",
    )

    count = models.PositiveIntegerField()

    unit = models.CharField(
        max_length=50,
        default="CFU/ml",
    )

class FungalCultureResult(models.Model):
    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="fungal_result",
    )

    colony_count = models.PositiveIntegerField()

    organism_name = models.CharField(
        max_length=200,
        blank=True,
    )

