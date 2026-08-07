from django import forms
from .models import Sample

class SampleForm(forms.ModelForm):

    class Meta:
        model = Sample

        exclude = (
            "registered_by",
            "case_code",
            "laboratory",
            "status",
            "created_at",
            "updated_at",
        )


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        field_classes = {
            "history": "carcass swab",
            "source_of_birds": "carcass",
            "source_of_water": "water",
            "feed_type": "feed carcass",
            "last_vaccination": "carcass",
            "antibiotics_used": "carcass",
            "mortality_pattern": "carcass",
            "pathology": "carcass",
            "remarks": "all",
        }

        for name, css in field_classes.items():
            if name in self.fields:
                existing = self.fields[name].widget.attrs.get("class", "")
                self.fields[name].widget.attrs["class"] = (
                        existing + " " + css
                ).strip()