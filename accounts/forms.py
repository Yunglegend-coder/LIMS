from django import forms

from .models import UserProfile


class UserSignatureForm(forms.ModelForm):
    signature = forms.ImageField(
        required=False,
        help_text="Upload a PNG or JPG signature image (maximum 5 MB).",
    )

    class Meta:
        model = UserProfile
        fields = ["signature"]

    def clean_signature(self):
        signature = self.cleaned_data.get("signature")
        if signature and signature.size > 5 * 1024 * 1024:
            raise forms.ValidationError("The signature image must be 5 MB or smaller.")
        if signature and getattr(signature, "image", None):
            width, height = signature.image.size
            if width > 3000 or height > 2000:
                raise forms.ValidationError("The signature image must be no larger than 3000 × 2000 pixels.")
        return signature
