from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
CHOICES = (
    ('fixed', 'Fixed Discount $'),
    ('percentage', 'Percentage Discount %')
)


class DiscountForm(forms.Form):
    discount_name = forms.CharField(max_length=200, required=True, widget=forms.TextInput(
        attrs={
            'class': 'form-control',
            'placeholder': 'Insert a name code'
        }
    ))
    discount_value = forms.IntegerField(required=True, widget=forms.NumberInput(
        attrs={
            'class': 'form-control',
            'placeholder': 'Insert your discount'
        }),
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),

    ])

    def __init__(self, data=None, *args, **kwargs):
        super(DiscountForm, self).__init__(data, *args, **kwargs)


class GetDiscountForm(forms.Form):
    member_number = forms.IntegerField(required=True, widget=forms.TextInput(
        attrs={
            'class': 'form-control',
            'placeholder': 'Insert your member number here'
        }
    ))

    def __init__(self, data=None, *args, **kwargs):
        super(GetDiscountForm, self).__init__(data, *args, **kwargs)
