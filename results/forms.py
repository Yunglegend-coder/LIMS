from django import forms
from django.forms import inlineformset_factory

from .models import (
    AssayResult,
    BinaryResult,
    GramStainResult,
    ASTResult,
    ASTResultItem,
    NDHIResult,
    PCRResult,
    TSIResult,
    CultureResult
)


# ============================================================
# BINARY
# ============================================================

class BinaryResultForm(forms.ModelForm):

    remarks = forms.CharField(
        required=False,
        label="Remarks",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Enter any relevant observations or remarks..."
                ),
            }
        ),
    )

    class Meta:
        model = BinaryResult
        fields = ["result"]

        widgets = {
            "result": forms.RadioSelect(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def save(self, commit=True, *, assay_result=None):

        if assay_result is None:
            raise ValueError("assay_result is required.")

        binary_result = super().save(commit=False)

        binary_result.assay_result = assay_result

        if commit:
            binary_result.save()

            assay_result.remarks = self.cleaned_data["remarks"]

            assay_result.save(
                update_fields=["remarks"]
            )

        return binary_result


# ============================================================
# GRAM STAIN
# ============================================================

class GramStainResultForm(forms.ModelForm):

    remarks = forms.CharField(
        required=False,
        label="Remarks",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Enter any relevant observations or remarks..."
                ),
            }
        ),
    )

    class Meta:
        model = GramStainResult
        fields = ["result"]

        widgets = {
            "result": forms.RadioSelect(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def save(self, commit=True, *, assay_result=None):

        if assay_result is None:
            raise ValueError("assay_result is required.")

        gram_result = super().save(commit=False)

        gram_result.assay_result = assay_result

        if commit:
            gram_result.save()

            assay_result.remarks = self.cleaned_data["remarks"]

            assay_result.save(
                update_fields=["remarks"]
            )

        return gram_result

# ============================================================
# TSI
# ============================================================
class TSIResultForm(forms.ModelForm):

    remarks = forms.CharField(
        required=False,
        label="Remarks",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Enter any relevant observations or remarks..."
                ),
            }
        ),
    )

    class Meta:
        model = TSIResult
        fields = ["result"]

        widgets = {
            "result": forms.RadioSelect(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def save(self, commit=True, *, assay_result=None):

        if assay_result is None:
            raise ValueError("assay_result is required.")

        tsi_result = super().save(commit=False)

        tsi_result.assay_result = assay_result

        if commit:
            tsi_result.save()

            assay_result.remarks = self.cleaned_data["remarks"]

            assay_result.save(
                update_fields=["remarks"]
            )

        return tsi_result


# ============================================================
# AST
# ============================================================

class ASTResultForm(forms.ModelForm):

    remarks = forms.CharField(
        required=False,
        label="Remarks",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Enter any relevant observations or remarks..."
                ),
            }
        ),
    )

    class Meta:
        model = ASTResult
        fields = []

    def save(self, commit=True, *, assay_result=None):

        if assay_result is None:
            raise ValueError("assay_result is required.")

        ast_result = super().save(commit=False)

        ast_result.assay_result = assay_result

        if commit:
            ast_result.save()

            assay_result.remarks = self.cleaned_data["remarks"]

            assay_result.save(
                update_fields=["remarks"]
            )

        return ast_result


ASTResultItemFormSet = inlineformset_factory(
    ASTResult,
    ASTResultItem,
    fields=[
        "antibiotic",
        "interpretation",
    ],
    extra=1,
    can_delete=True,
    widgets={
        "antibiotic": forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        "interpretation": forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    },
)


# ============================================================
# NDHI
# ============================================================

class NDHIResultForm(forms.ModelForm):

    remarks = forms.CharField(
        required=False,
        label="Remarks",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Enter any relevant observations or remarks..."
                ),
            }
        ),
    )

    class Meta:
        model = NDHIResult
        fields = ["result"]

        widgets = {
            "result": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "Enter NDHI result..."
                    ),
                }
            ),
        }

    def save(self, commit=True, *, assay_result=None):

        if assay_result is None:
            raise ValueError("assay_result is required.")

        ndhi_result = super().save(commit=False)

        ndhi_result.assay_result = assay_result

        if commit:
            ndhi_result.save()

            assay_result.remarks = self.cleaned_data["remarks"]

            assay_result.save(
                update_fields=["remarks"]
            )

        return ndhi_result


# ============================================================
# PCR
# ============================================================

class PCRResultForm(forms.ModelForm):

    remarks = forms.CharField(
        required=False,
        label="Remarks",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Enter any relevant observations or remarks..."
                ),
            }
        ),
    )

    class Meta:
        model = PCRResult

        fields = [
            "target",
            "cq_ct",
            "result",
            "interpretation",
            "picture",
        ]

        widgets = {
            "target": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter PCR target...",
                }
            ),
            "cq_ct": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Cq/Ct value",
                }
            ),
            "result": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Positive / Negative",
                }
            ),
            "interpretation": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter interpretation...",
                }
            ),
            "picture": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*,.pdf",
                }
            ),
        }

    def save(self, commit=True, *, assay_result=None):

        if assay_result is None:
            raise ValueError("assay_result is required.")

        pcr_result = super().save(commit=False)

        pcr_result.assay_result = assay_result

        if commit:
            pcr_result.save()

            assay_result.remarks = self.cleaned_data["remarks"]

            assay_result.save(
                update_fields=["remarks"]
            )

        return pcr_result

# ============================================================
# CULTURE
# ============================================================

class CultureResultForm(forms.ModelForm):

    remarks = forms.CharField(
        required=False,
        label="Remarks",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Enter any relevant observations or remarks..."
                ),
            }
        ),
    )

    class Meta:
        model = CultureResult

        fields = [
            "growth",
            "organism_name",
            "colony_description",
            "identification_notes",
        ]

        widgets = {

            "growth": forms.RadioSelect(
                attrs={
                    "class": "form-check-input",
                }
            ),

            "organism_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Enter organism identified..."
                    ),
                }
            ),

            "colony_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Describe colony morphology..."
                    ),
                }
            ),

            "identification_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Enter identification details, "
                        "biochemical findings, etc..."
                    ),
                }
            ),
        }

    def save(self, commit=True, *, assay_result=None):

        if assay_result is None:
            raise ValueError(
                "assay_result is required."
            )

        culture_result = super().save(
            commit=False
        )

        culture_result.assay_result = assay_result

        if commit:

            culture_result.save()

            assay_result.remarks = (
                self.cleaned_data["remarks"]
            )

            assay_result.save(
                update_fields=["remarks"]
            )

        return culture_result