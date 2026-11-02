from django import forms
from django.core.exceptions import ValidationError
from .models import Order, PaymentOption, Print, Review, TShirtColor
from .validators import normalize_phone, normalize_instagram, validate_image


class HoneyForm(forms.Form):
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise ValidationError("We couldn't submit this form. Please reload and try again.")
        return ""


class OrderForm(HoneyForm, forms.ModelForm):
    phone = forms.CharField(max_length=25, widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "98XXXXXXXX"}))
    submission_key = forms.UUIDField(widget=forms.HiddenInput)
    design_image = forms.ImageField(validators=[validate_image])
    payment_screenshot = forms.ImageField(required=False, validators=[validate_image])
    terms = forms.BooleanField(error_messages={"required": "Please confirm the design and delivery details."})

    class Meta:
        model = Order
        fields = ["color", "print", "placement", "print_scale", "full_name", "instagram_username", "phone", "province", "district", "municipality", "ward", "landmark", "size", "quantity", "notes", "payment_method"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "phone": forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "98XXXXXXXX"}),
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "instagram_username": forms.TextInput(attrs={"placeholder": "@yourhandle", "autocapitalize": "none"}),
            "ward": forms.NumberInput(attrs={"min": 1, "max": 35}),
            "quantity": forms.NumberInput(attrs={"min": 1, "max": 20, "value": 1}),
        }

    def __init__(self, *args, checkout_keys=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.checkout_keys = checkout_keys
        self.fields["color"].queryset = TShirtColor.objects.filter(is_active=True)
        self.fields["print"].queryset = Print.objects.filter(is_active=True)
        # Form-level length permits an optional country code; stored value stays 10 digits.
        self.fields["phone"].max_length = 25
        self.fields["phone"].widget.attrs["maxlength"] = 25
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])

    def clean_instagram_username(self):
        return normalize_instagram(self.cleaned_data.get("instagram_username", ""))

    def clean_submission_key(self):
        key = self.cleaned_data["submission_key"]
        if str(key) not in self.checkout_keys:
            raise ValidationError("Your checkout expired. Reload the designer to start a fresh order.")
        return key

    def clean(self):
        data = super().clean()
        method = data.get("payment_method")
        if method and method != "cod":
            if not PaymentOption.objects.filter(provider=method, is_active=True).exists():
                self.add_error("payment_method", "This payment method is not available yet. Choose cash on delivery.")
            if not data.get("payment_screenshot"):
                self.add_error("payment_screenshot", "Upload the payment screenshot for manual verification.")
        return data


class ReviewForm(HoneyForm, forms.ModelForm):
    consent = forms.BooleanField(label="You may publish my review, name, username and optional photo after moderation.")

    class Meta:
        model = Review
        fields = ["name", "instagram_username", "rating", "text", "photo"]
        widgets = {"text": forms.Textarea(attrs={"rows": 4, "placeholder": "How did you make it yours?"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")

    def clean_instagram_username(self):
        return normalize_instagram(self.cleaned_data.get("instagram_username", ""))


class TrackingForm(HoneyForm):
    number = forms.CharField(max_length=25, label="Order ID", widget=forms.TextInput(attrs={"placeholder": "BW-YYMMDD-XXXXXXXXXX", "autocapitalize": "characters"}))
    phone = forms.CharField(max_length=25, widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}))

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])

    def clean_number(self):
        return self.cleaned_data["number"].strip().upper()
