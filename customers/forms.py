from django import forms

from .models import Customer
from django.db.models import Q
from django.forms import inlineformset_factory
from locations.models import Farm


class CustomerForm(forms.ModelForm):

    class Meta:
        model = Customer

        fields = [
            "name",
            "email",
            "whatsapp",
            "state",
            "address",
        ]

        widgets = {
            "address": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }


class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ("name", "state", "address")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


CustomerFarmFormSet = inlineformset_factory(
    Customer,
    Farm,
    form=FarmForm,
    extra=1,
    can_delete=True,
)


class CustomerEmailCampaignForm(forms.Form):
    customers = forms.ModelMultipleChoiceField(
        queryset=Customer.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Customers",
    )
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"class": "form-control"}))
    body = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 8}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customers"].queryset = Customer.objects.exclude(
            Q(email="") | Q(email__isnull=True)
        ).order_by("name")
