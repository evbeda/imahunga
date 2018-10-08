from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
CHOICES = (
    ('fixed', 'Fixed Discount $'),
    ('percentage', 'Percentage Discount %')
)


class DiscountForm(forms.Form):
    discount_name = forms.CharField(max_length=200, required=True, widget=forms.TextInput(
        attrs={
            'class': 'form-control'
        }
    ))
    discount_value = forms.IntegerField(required=True, widget=forms.NumberInput(
        attrs={
            'class': 'form-control'
        }),
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
    ])

    def __init__(self, data=None, *args, **kwargs):
        super(DiscountForm, self).__init__(data, *args, **kwargs)
