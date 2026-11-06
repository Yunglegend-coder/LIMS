from django.conf import settings
from django.db import models

from assays.models import AssayOrder
from samples.models import Sample


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
        return (
            f"{self.assay_order.sample.case_code} - "
            f"{self.assay_order.assay.name}"
        )


class SampleReport(models.Model):
    """Editable narrative fields included in a sample's final report."""

    sample = models.OneToOneField(
        Sample,
        on_delete=models.CASCADE,
        related_name="report",
    )
    clinical_diagnosis = models.TextField(blank=True)
    laboratory_diagnosis = models.TextField(blank=True)
    isolate = models.CharField(max_length=200, blank=True)
    comments_recommendations = models.TextField(blank=True)
    carcass_count = models.PositiveSmallIntegerField(null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_sample_reports",
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report narrative - {self.sample.case_code}"


class PathologyFinding(models.Model):
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SampleReportFinding(models.Model):
    sample_report = models.ForeignKey(
        SampleReport,
        on_delete=models.CASCADE,
        related_name="pathology_findings",
    )
    finding = models.ForeignKey(
        PathologyFinding,
        on_delete=models.PROTECT,
        related_name="sample_findings",
    )
    carcass_count = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["finding__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["sample_report", "finding"],
                name="unique_pathology_per_sample_report",
            ),
            models.CheckConstraint(
                condition=models.Q(carcass_count__gte=1),
                name="sample_report_finding_count_positive",
            ),
        ]

    def __str__(self):
        return f"{self.finding}: {self.carcass_count} carcass(es)"


# ============================================================
# BINARY RESULT
# ============================================================

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


# ============================================================
# GRAM STAIN
# ============================================================

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

    def __str__(self):
        return self.get_result_display()

# ============================================================
# TSI
# ============================================================
class TSIChoice(models.TextChoices):
    # No reaction
    NO_REACTION = "NO REACTION", "NO REACTION"

    # Alkaline slant / Alkaline butt
    K_K = "K/K", "K/K"
    K_K_G = "K/K G", "K/K Gas"
    K_K_H2S = "K/K H2S", "K/K H2S"
    K_K_G_H2S = "K/K G H2S", "K/K Gas + H2S"

    # Alkaline slant / Acid butt
    K_A = "K/A", "K/A"
    K_A_G = "K/A G", "K/A Gas"
    K_A_H2S = "K/A H2S", "K/A H2S"
    K_A_G_H2S = "K/A G H2S", "K/A Gas + H2S"

    # Acid slant / Acid butt
    A_A = "A/A", "A/A"
    A_A_G = "A/A G", "A/A Gas"
    A_A_H2S = "A/A H2S", "A/A H2S"
    A_A_G_H2S = "A/A G H2S", "A/A Gas + H2S"

    # Acid slant / Alkaline butt (rare)
    A_K = "A/K", "A/K"
    A_K_G = "A/K G", "A/K Gas"
    A_K_H2S = "A/K H2S", "A/K H2S"
    A_K_G_H2S = "A/K G H2S", "A/K Gas + H2S"

    # Alkaline slant / No change butt
    K_N = "K/N", "K/N"
    K_N_G = "K/N G", "K/N Gas"
    K_N_H2S = "K/N H2S", "K/N H2S"
    K_N_G_H2S = "K/N G H2S", "K/N Gas + H2S"

    # Acid slant / No change butt
    A_N = "A/N", "A/N"
    A_N_G = "A/N G", "A/N Gas"
    A_N_H2S = "A/N H2S", "A/N H2S"
    A_N_G_H2S = "A/N G H2S", "A/N Gas + H2S"

    # No change slant / Acid butt
    N_A = "N/A", "N/A"
    N_A_G = "N/A G", "N/A Gas"
    N_A_H2S = "N/A H2S", "N/A H2S"
    N_A_G_H2S = "N/A G H2S", "N/A Gas + H2S"

    # No change slant / Alkaline butt
    N_K = "N/K", "N/K"
    N_K_G = "N/K G", "N/K Gas"
    N_K_H2S = "N/K H2S", "N/K H2S"
    N_K_G_H2S = "N/K G H2S", "N/K Gas + H2S"

    # No change slant / No change butt
    N_N = "N/N", "N/N"
    N_N_G = "N/N G", "N/N Gas"
    N_N_H2S = "N/N H2S", "N/N H2S"
    N_N_G_H2S = "N/N G H2S", "N/N Gas + H2S"

class TSIResult(models.Model):

    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="tsi_result",
    )

    result = models.CharField(
        max_length=20,
        choices=TSIChoice.choices,
    )

    def __str__(self):
        return self.get_result_display()



# ============================================================
# AST
# ============================================================

class Antibiotic(models.Model):

    code = models.CharField(
        max_length=10,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

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

    def __str__(self):
        return (
            f"AST - "
            f"{self.assay_result.assay_order.sample.case_code}"
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

    def __str__(self):
        return (
            f"{self.antibiotic.code} - "
            f"{self.get_interpretation_display()}"
        )


# ============================================================
# INSTRUMENT RESULT
# ============================================================

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


# ============================================================
# COUNT RESULT
# ============================================================

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


# ============================================================
# FUNGAL CULTURE
# ============================================================

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

# ============================================================
# CULTURE
# ============================================================

class CultureGrowthChoice(models.TextChoices):

    NO_GROWTH = "NO_GROWTH", "No Growth"
    GROWTH = "GROWTH", "Growth"


class CultureResult(models.Model):

    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="culture_result",
    )

    growth = models.CharField(
        max_length=20,
        choices=CultureGrowthChoice.choices,
    )

    organism_name = models.CharField(
        max_length=200,
        blank=True,
    )

    colony_description = models.TextField(
        blank=True,
    )

    identification_notes = models.TextField(
        blank=True,
    )

    def __str__(self):
        return (
            f"Culture - "
            f"{self.assay_result.assay_order.sample.case_code}"
        )


# ============================================================
# NDHI
# ============================================================

class NDHIResult(models.Model):

    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="ndhi_result",
    )

    result = models.TextField()

    def __str__(self):
        return (
            f"NDHI - "
            f"{self.assay_result.assay_order.sample.case_code}"
        )


# ============================================================
# PCR
# ============================================================

class PCRResult(models.Model):

    assay_result = models.OneToOneField(
        AssayResult,
        on_delete=models.CASCADE,
        related_name="pcr_result",
    )

    target = models.CharField(
        max_length=200,
    )

    cq_ct = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    result = models.CharField(
        max_length=100,
    )

    interpretation = models.CharField(
        max_length=200,
        blank=True,
    )

    picture = models.FileField(
        upload_to="pcr_results/",
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"PCR - "
            f"{self.target} - "
            f"{self.assay_result.assay_order.sample.case_code}"
        )
