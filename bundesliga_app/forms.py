from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import ugettext_lazy as _
from .models import (
    Event,
    EventTicketType,
    Discount,
)
from .utils import (
    get_event_eb_api,
    get_auth_token,
    validate_member_number_ds,
    get_ticket_type
)
from django.contrib.auth import get_user_model
CHOICES = (
    ('fixed', 'Fixed Discount $'),
    ('percentage', 'Percentage Discount %')
)


class DiscountForm(forms.Form):
    discount_name = forms.CharField(max_length=200, required=True, widget=forms.TextInput(
        attrs={
            'class': 'form-control',
            'placeholder': _('Insert a name code')
        }
    ))
    discount_value = forms.IntegerField(required=True, widget=forms.NumberInput(
        attrs={
            'class': 'form-control',
            'placeholder': _('Insert your discount')
        }),
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),

    ])

    ticket_type = forms.CharField(max_length=200, required=True, widget=forms.TextInput(
        attrs={
            'class': 'form-control',
            'readonly': 'readonly',
        }
    ))

    def is_valid(self):
        valid = super(DiscountForm, self).is_valid()

        if not valid:
            return valid
        valid_free = get_event_eb_api(
            get_auth_token(self.user),
            self.event.event_id,
        )['is_free']
        if valid_free:
            self.add_error(
                '__all__',
                _('You cant create a discount in a free event'),
            )
            return False
        valid_free_ticket = get_ticket_type(
            self.user,
            self.event.event_id,
            self.ticket_type_id,
        )[self.ticket_type_id]['free']
        if valid_free_ticket:
            self.add_error(
                '__all__',
                _('You cant create a discount for a free ticket'),
            )
            return False
        if not self.discount_id:
            discount = Discount.objects.filter(
                ticket_type=self.ticket_type_id
            )
            if len(discount) > 0:
                self.add_error(
                    '__all__',
                    _('You already have a discount for this ticket type'),
                )
                return False
            return True
        return True

    def __init__(self, data=None, *args, **kwargs):
        event_id = kwargs.pop('event_id', None)
        self.ticket_type_id = kwargs.pop('ticket_type_id', None)
        self.discount_id = kwargs.pop('discount_id', None)
        self.user = kwargs.pop('user', None)
        super(DiscountForm, self).__init__(data, *args, **kwargs)
        self.event = Event.objects.get(
            id=event_id,
            is_active=True,
        )
        self.ticket_type = get_ticket_type(
            self.user,
            self.event.event_id,
            self.ticket_type_id,
        )
        # If no data, so its when the form is being created,
        # so we set the ticket type value and the user
        if not data:
            self.fields['ticket_type'].initial = self.ticket_type[self.ticket_type_id]['name']


class GetDiscountForm(forms.Form):
    tickets_type = forms.ChoiceField(widget=forms.Select(
        attrs={
            'class': 'custom-select'
        }
    ))
    member_number_1 = forms.IntegerField(required=True, widget=forms.NumberInput(
        attrs={
            'class': 'form-control',
            'placeholder': _('Insert your member number here')
        }
    ))

    def is_valid(self):
        super(GetDiscountForm, self).is_valid()
        """ This method calls the API of DS in utils
        and returns a string according to the response
        """
        invalid_numbers = []
        for number in range(1, len(self.cleaned_data)):
            return_api_ds = validate_member_number_ds(
                self.cleaned_data['member_number_{}'.format(number)]
            )

            if return_api_ds == 'Invalid Request':
                self.add_error('member_number_{}'.format(
                    number), _('Invalid request'))
                return False
            else:
                if not ('Kartentyp' in return_api_ds):
                    invalid_numbers.append(
                        str(
                            self.cleaned_data['member_number_{}'.format(
                                number)]
                        )
                    )

        if invalid_numbers:
            numbers = ', '.join(invalid_numbers)
            if len(invalid_numbers) == 1:
                self.add_error(
                    'member_number_1',
                    _('Invalid number ')+'{}'.format(numbers),
                )
            else:
                self.add_error(
                    'member_number_1',
                    _('Invalid numbers ')+'{}'.format(numbers),
                )
            return False
        else:
            return True

    def __init__(self, data=None, *args, **kwargs):
        event_id = kwargs.pop('event_id', None)
        user_id = kwargs.pop('user', None)
        super(GetDiscountForm, self).__init__(data, *args, **kwargs)
        max_members = 11
        for member in range(2, max_members):
            field_name = "member_number_{}".format(member)
            self.fields[field_name] = forms.IntegerField()
        user = get_user_model().objects.get(
            id=user_id)
        ticket_types = self.get_ticket_types(event_id, user)
        self.fields['tickets_type'].choices = ticket_types

    def get_ticket_types(self, event_id, user):
        event = Event.objects.get(
            id=event_id,
            is_active=True,
        )
        tickets_in_db = EventTicketType.objects.filter(
            event=event
        )
        # Add tickets with discount
        tickets_with_discount = {}

        for ticket_in_db in tickets_in_db:
            if Discount.objects.filter(ticket_type=ticket_in_db).exists():
                tickets_with_discount[ticket_in_db.id] = ticket_in_db.__dict__

        tickets_types_name = ()
        for ticket in tickets_with_discount:
            ticket_type_eb = get_ticket_type(
                user,
                event.event_id,
                ticket,
            )
            tickets_types_name = ((ticket, ticket_type_eb[str(ticket)]['name']),) + tickets_types_name
        return tickets_types_name
