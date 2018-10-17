from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from .utils import (
    validate_member_number_ds,
)
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
    member_number = forms.IntegerField(required=True, widget=forms.NumberInput(
        attrs={
            'class': 'form-control',
            'placeholder': 'Insert your member number here'
        }
    ))

    def is_valid(self):
        valid = super(GetDiscountForm, self).is_valid()

        if not valid:
            return valid

        """ This method calls the API of DS in utils
        and returns a string according to the response
        """
        return_api_ds = validate_member_number_ds(
            self.cleaned_data['member_number']
        )

        if return_api_ds == 'Invalid Request':
            self.add_error('member_number', 'Invalid request')
            return False
        else:
            if 'Kartentyp' in return_api_ds:
                # If valid member number
                return True
            else:
                # If not valid member number
                self.add_error('member_number', 'Invalid number')
                return False

    def __init__(self, data=None, *args, **kwargs):
        super(GetDiscountForm, self).__init__(data, *args, **kwargs)
