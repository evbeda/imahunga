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
    discount_type = forms.ChoiceField(choices=CHOICES, widget=forms.Select(
        attrs={
            'class': 'form-control'
        }
    ))
    discount_value = forms.FloatField(required=True, widget=forms.NumberInput(
        attrs={
            'class': 'form-control'
        }
    ))

    def __init__(self, data=None, *args, **kwargs):
        super(DiscountForm, self).__init__(data, *args, **kwargs)
        if data and data.get('discount_type', CHOICES[0][1]) == CHOICES[0][0]:
            self.fields['discount_value'].validators = [MinValueValidator(0)]
        elif data and data.get('discount_type', CHOICES[1][1]) == CHOICES[1][0]:
            self.fields['discount_value'].validators = [
                MinValueValidator(0),
                MaxValueValidator(100)
            ]
