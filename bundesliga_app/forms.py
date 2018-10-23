from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from .utils import (
    validate_member_number_ds,
)
from django.forms import formset_factory

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
            'placeholder': 'Insert your discount',
        }),
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),

    ])

    def __init__(self, data=None, *args, **kwargs):
        super(DiscountForm, self).__init__(data, *args, **kwargs)


class GetDiscountForm(forms.Form):

    member_number_0 = forms.IntegerField(required=True, widget=forms.NumberInput(
        attrs={
            'class': 'form-control',
            'placeholder': 'Insert your member number here',
        }
    ))

    def is_valid(self):

        super(GetDiscountForm, self).is_valid()
        # results = {}

        """ This method calls the API of DS in utils
        and returns a string according to the response
        """
        invalid_numbers = []
        for number in range(len(self.cleaned_data)):
            return_api_ds = validate_member_number_ds(
                self.cleaned_data['member_number_{}'.format(number)]
            )

            if return_api_ds == 'Invalid Request':
                self.add_error('member_number_{}'.format(number), 'Invalid request')
                # results['member_number_{}'.format(number)] = False
                return False
            else:
                if not ('Kartentyp' in return_api_ds):
                    # If valid member number
                    # results['member_number_{}'.format(number)] = True
                    # If not valid member number
                    invalid_numbers.append(number)
                    # results['member_number_{}'.format(number)] = True

        if invalid_numbers:
            import ipdb; ipdb.set_trace()
            for i in range(len(invalid_numbers)):
                self.add_error(
                    'member_number_{}'.format(invalid_numbers[i]),
                    'Invalid numbers {}'.format(self.cleaned_data['member_number_{}'.format(invalid_numbers[i])]),
                )
        return invalid_numbers

    def discount_already_used(self):
        self.add_error('member_number',
                       'You already used the discount for this event')

    def __init__(self, data=None, *args, **kwargs):
        super(GetDiscountForm, self).__init__(data, *args, **kwargs)
        max_members = 10
        for member in range(1, max_members):
            field_name = "member_number_{}".format(member)
            self.fields[field_name] = forms.IntegerField(required=True)
