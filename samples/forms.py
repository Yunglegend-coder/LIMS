from django import forms
from django.conf import settings

from core.utils.case_code import generate_case_code
from .models import Sample
from .choices import DocSubtype, SampleType

class SampleForm(forms.ModelForm):
    case_code = forms.CharField(
        required=False,
        max_length=20,
        label="Case code",
        help_text="Keep the suggested code, or enter a unique code manually.",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    doc_subtypes = forms.MultipleChoiceField(
        choices=DocSubtype.choices,
        required=False,
        label="DOC materials included",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Sample

        exclude = (
            "registered_by",
            "laboratory",
            "status",
            "created_at",
            "updated_at",
        )

        labels = {
            "age": "Age",
            "breed_species": "Breed/Species",
            "source_of_birds": "Source of Birds",
            "feed_type": "Feed",
            "population": "Population",
            "source_of_water": "Water Source",
            "housing": "Housing",
            "major_complaint": "Major Complaint",
            "mortality_pattern": "Mortality pattern",
            "medication": "Medication",
            "vaccination_history": "Vaccination History",
            "drugs": "Drugs",
            "vaccination": "Vaccination",
            "last_vaccination": "Last vaccination date",
        }

        widgets = {
            "age": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 24 weeks"}),
            "breed_species": forms.TextInput(attrs={"class": "form-control"}),
            "population": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "housing": forms.TextInput(attrs={"class": "form-control"}),
            "major_complaint": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "medication": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "vaccination_history": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "drugs": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "vaccination": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "source_of_birds": forms.TextInput(attrs={"class": "form-control"}),
            "source_of_water": forms.TextInput(attrs={"class": "form-control"}),
            "feed_type": forms.TextInput(attrs={"class": "form-control"}),
            "mortality_pattern": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "last_vaccination": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.fields["sample_type"].widget.attrs["class"] = "form-select"
        self.fields["doc_subtypes"].initial = (
            self.instance.doc_subtypes
            if self.instance.pk
            else list(DocSubtype.values)
        )
        if not self.is_bound and not self.instance.pk:
            self.fields["case_code"].initial = generate_case_code(settings.LAB_CODE)

        field_classes = {
            "age": "carcass",
            "breed_species": "carcass",
            "source_of_birds": "carcass",
            "source_of_water": "water",
            "feed_type": "feed carcass",
            "population": "carcass",
            "housing": "carcass",
            "major_complaint": "carcass",
            "last_vaccination": "carcass",
            "drugs": "carcass",
            "medication": "carcass",
            "vaccination_history": "carcass",
            "vaccination": "carcass",
            "mortality_pattern": "carcass",
            "remarks": "all",
        }

        for name, css in field_classes.items():
            if name in self.fields:
                existing = self.fields[name].widget.attrs.get("class", "")
                self.fields[name].widget.attrs["class"] = (
                        existing + " " + css
                ).strip()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("sample_type") != SampleType.DOC:
            cleaned["doc_subtypes"] = []
        return cleaned
