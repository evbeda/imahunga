from bundesliga_app.models import Event
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from .models import Discount
from .utils import (
    get_auth_token,
    get_event_eb_api,
    get_events_user_eb_api,
    get_user_eb_api,
    get_venue_eb_api,
    get_event_tickets_eb_api,
    validate_member_number_ds,
    EventAccessMixin,
    DiscountAccessMixin,
    post_discount_code_to_eb,
    check_discount_code_in_eb,
)
from .forms import (
    DiscountForm,
    GetDiscountForm,
)
from django.views.generic.edit import (
    FormView,
    DeleteView,
)
from django.forms.utils import ErrorList
from django.contrib.auth import get_user_model
from dateutil import parser


@method_decorator(login_required, name='dispatch')
class HomeView(TemplateView, LoginRequiredMixin):

    """ This is the index view.
    Here we show all the events of the user in our app """

    template_name = 'index.html'

    # Get all the data of organizer'events from EB API
    def _get_events(self):
        # Dictionary for events
        events = {}
        # Get all active events from DB
        events_own = Event.objects.filter(
            organizer=self.request.user).filter(is_active=True)
        for event in events_own:
            """ Add event to dictionary with the id as key
            and event from API as value """
            events[event.id] = get_event_eb_api(
                get_auth_token(self.request.user),
                event.event_id,
            )
            # Add local_date format
            events[event.id]['start_date'] = parser.parse(
                events[event.id]['start']['local'])
            events[event.id]['end_date'] = parser.parse(
                events[event.id]['end']['local'])
            # Add discount of the event
            discount = Discount.objects.filter(
                event=event.id
            )
            if discount:
                """ If the event is free at the moment to load the page it will
                delete the discount in our database"""
                if events[event.id]['is_free']:
                    Discount.objects.filter(
                        event=event.id
                    ).delete()
                else:
                    events[event.id]['discount'] = discount.get().value
                    events[event.id]['discount_type'] = discount.get().value_type
        return events

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['events'] = self._get_events()
        context['organizer'] = self.request.user
        context['attendee_url'] = self.request.get_host() + reverse(
            'landing_page_buyer',
            kwargs={
                'organizer_id': context['organizer'].id
            },)

        return context


@method_decorator(login_required, name='dispatch')
class SelectEvents(TemplateView, LoginRequiredMixin):

    """ This is the select events view. Here we display all the events
    of the organizer from EB
     """

    template_name = 'organizer/select_events.html'

    def _get_event(self):
        return get_events_user_eb_api(
            get_auth_token(self.request.user)
        )

    def post(self, *args, **kwargs):
        events = self._get_event()
        request_body_elements = str(self.request.body).split('event_')
        request_body_elements.pop(0)
        events_id = []
        # Put in array all the events id selected
        for event_id in request_body_elements:
            event = event_id.split('=')
            events_id.append(event[0])
        """
            See if had unselected any event active
            and delete every discount that has associated
        """
        db_selected_ids = []
        for event in Event.objects.filter(organizer=self.request.user).filter(is_active=True):
            db_selected_ids.append(event.event_id)
        for db_event_id in db_selected_ids:
            if db_event_id not in events_id:
                event_in_db = Event.objects.filter(
                    event_id=db_event_id)
                event_in_db.update(is_active=False)
                event_in_db = event_in_db.get()
                event_discounts = Discount.objects.filter(
                    event=event_in_db
                )
                if event_discounts:
                    Discount.objects.filter(
                            event=event_in_db
                        ).delete()
        # For each event in the api, verify if the selected ones are corrects
        for event_in_api in events:
            # If the event id is an event of organizer
            if event_in_api['id'] in events_id:
                # Verify if this event already exist
                if not Event.objects.filter(event_id=event_in_api['id']).exists():
                    Event.objects.create(
                        event_id=event_in_api['id'],
                        organizer=self.request.user,
                        is_active=True,
                    )
                else:
                    Event.objects.filter(event_id=event_in_api['id']).update(
                        event_id=event_in_api['id'],
                        organizer=self.request.user,
                        is_active=True,
                    )
        return HttpResponseRedirect(reverse('index'))

    def get_context_data(self, **kwargs):
        context = super(SelectEvents, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['me'] = get_user_eb_api(
            get_auth_token(self.request.user)
        )
        context['already_selected_id'] = []
        for event in Event.objects.filter(
                organizer=self.request.user).filter(is_active=True):
            context['already_selected_id'].append(event.event_id)
        # Bring live events of user
        context['events'] = self._get_event()
        # Add local_date format
        for event in context['events']:
            event['start_date'] = parser.parse(
                event['start']['local'])
            event['end_date'] = parser.parse(
                event['end']['local'])
        return context


@method_decorator(login_required, name='dispatch')
class EventDiscountsView(TemplateView, LoginRequiredMixin, EventAccessMixin):

    """ This is the the Event Discounts view,
    here the organizer can manage the discounts of the event"""

    template_name = 'organizer/event_discounts.html'

    def get_context_data(self, **kwargs):
        context = super(EventDiscountsView, self).get_context_data(**kwargs)
        # Get event by id in kwargs
        context['event'] = self.get_event()
        # Get event name in EB API
        context['id'] = self.kwargs['event_id']
        context['discounts'] = Discount.objects.filter(
            event=context['event']
        )
        context['event_name'] = get_event_eb_api(
            get_auth_token(self.request.user),
            context['event'].event_id,
        )['name']['text']
        return context


@method_decorator(login_required, name='dispatch')
class ManageDiscount(FormView, LoginRequiredMixin, DiscountAccessMixin):

    form_class = DiscountForm
    template_name = 'organizer/create_discount.html'

    def get_form_kwargs(self):
        kwargs = super(ManageDiscount, self).get_form_kwargs()
        if 'discount_id' in self.kwargs:
            discount = self.get_discount()
            if discount:
                kwargs['initial']['discount_name'] = discount.name
                kwargs['initial']['discount_type'] = discount.value_type
                kwargs['initial']['discount_value'] = discount.value
        return kwargs

    def post(self, request, *args, **kwargs):
        form = DiscountForm(
            request.POST
        )
        valid_free = get_event_eb_api(
            get_auth_token(self.request.user),
            self.get_event().event_id,
        )['is_free']
        if valid_free:
            error = form.errors.setdefault('__all__', ErrorList())
            error.append(u'You cant create a discount in a free event')
            return self.form_invalid(form)
        if not ('discount_id' in self.kwargs):
            self._verify_event_discount(form)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.add_discount(form, self.get_event())
        return HttpResponseRedirect(
            reverse(
                'events_discount',
                kwargs={
                    'event_id': self.get_event().id
                },
            )
        )

    def add_discount(self, form, event):
        if not ('discount_id' in self.kwargs):
            Discount.objects.create(
                name=form['discount_name'].value(),
                event=event,
                value=form['discount_value'].value(),
                value_type='percentage',
            )
        else:
            Discount.objects.filter(pk=self.kwargs['discount_id']).update(
                name=form['discount_name'].value(),
                event=event,
                value=form['discount_value'].value(),
                value_type='percentage',
            )

    def _verify_event_discount(self, form):
        discount = Discount.objects.filter(
            event=self.get_event().id
        )
        if len(discount) > 0:
            error = form.errors.setdefault('__all__', ErrorList())
            error.append(u'You already have a discount for this event')

    def get_context_data(self, **kwargs):
        context = super(ManageDiscount, self).get_context_data(**kwargs)
        context['event'] = self.get_event()
        if 'discount_id' in self.kwargs:
            context['discount'] = get_object_or_404(
                Discount,
                id=self.kwargs['discount_id'],
            )
        return context


@method_decorator(login_required, name='dispatch')
class DeleteDiscountView(DeleteView, LoginRequiredMixin, DiscountAccessMixin):
    """ This is the delete discount view """
    model = Discount
    template_name = 'organizer/delete_discount.html'

    def get_success_url(self):
        return reverse_lazy(
            'events_discount',
            kwargs={'event_id': self.kwargs['event_id']},
        )

    def get_object(self):
        # import ipdb;ipdb.set_trace()
        return self.get_discount()

    def get_context_data(self, **kwargs):
        context = super(DeleteDiscountView, self).get_context_data(**kwargs)
        context['event'] = self.get_event()
        return context


""" -- Buyer Views -- """


class LandingPageBuyerView(TemplateView):
    """ This is the landing page of an organizer for the buyer """

    template_name = 'buyer/landing_page_buyer.html'

    def _get_events(self, organizer):
        # Dictionary for events
        events = {}
        # Get all active events from DB
        events_own = Event.objects.filter(
            organizer=organizer,
            is_active=True,
        )
        for event in events_own:
            """ Add event to dictionary with the id as key
            and event from API as value.
            It uses the token of landing page's organizer """
            events[event.id] = get_event_eb_api(
                get_auth_token(organizer),
                event.event_id,
            )

            # Get event venue
            events[event.id]['venue'] = get_venue_eb_api(
                get_auth_token(organizer),
                events[event.id]['venue_id'],
            )

            # Add local_date format
            events[event.id]['start_date'] = parser.parse(
                events[event.id]['start']['local'])
            events[event.id]['end_date'] = parser.parse(
                events[event.id]['end']['local'])
            # Add discount of the event
            discount = Discount.objects.filter(
                event=event.id
            )
            if discount:
                events[event.id]['discount'] = discount.get().value
                events[event.id]['discount_type'] = discount.get().value_type
        return events

    def get_context_data(self, **kwargs):
        context = super(LandingPageBuyerView, self).get_context_data(**kwargs)
        context['organizer'] = get_user_model().objects.get(
            id=self.kwargs['organizer_id'])
        context['events'] = self._get_events(
            context['organizer']
        )
        return context


class ListingPageEventView(TemplateView):
    """ This view visualize the info of an event """

    template_name = 'buyer/listing_page_event.html'

    def _get_events(self, organizer):
        # Get Event by the id and organizer
        event_in_db = get_object_or_404(
            Event,
            id=self.kwargs['event_id'],
            organizer=organizer,
        )
        """ Get the event from API EB.
            It uses the token of landing page's organizer """
        event = get_event_eb_api(
            get_auth_token(organizer),
            event_in_db.event_id,
        )
        # Add local_date format
        event['start_date'] = parser.parse(event['start']['local'])
        event['end_date'] = parser.parse(event['end']['local'])
        # Add discount of the event
        discount = Discount.objects.filter(
            event=event_in_db.id
        )
        if discount:
            event['discount'] = discount.get().value
            event['discount_type'] = discount.get().value_type
        return event

    def _get_venue(self, organizer, venue_id):
        # Return none if venue does not exist
        if venue_id is None:
            return None
        """ Get the venue from API EB.
            It uses the token of landing page's organizer """
        venue = get_venue_eb_api(
            get_auth_token(organizer),
            venue_id,
        )
        return venue

    def _get_tickets(self, organizer, event_id):
        tickets = get_event_tickets_eb_api(
            get_auth_token(organizer),
            event_id,
        )
        ticket_values = {
            'min_value': None,
            'min_value_display': None,
            'max_value': None,
            'max_value_display': None,
        }
        for ticket in tickets:
            # Free ticket, min value 0
            if ticket['free']:
                ticket_values['min_value'] = 0
                ticket_values['min_value_display'] = "$0.00"
            else:
                # Get the value of the ticket
                ticket_value = float(ticket['actual_cost']['major_value'])

                """ If the max value is not setted yet (first paid ticket for example),
                set max value with the ticket value """
                if ticket_values['max_value'] is None:
                    ticket_values['max_value'] = ticket_value
                    ticket_values['max_value_display'] = ticket['actual_cost']['display']

                """ If the min value is not setted yet (first paid ticket for example),
                set min value with the ticket value """
                if ticket_values['min_value'] is None:
                    ticket_values['min_value'] = ticket_value
                    ticket_values['min_value_display'] = ticket['actual_cost']['display']

                # If the actual ticket value is bigger than the actual max value
                if ticket_value > ticket_values['max_value']:
                    ticket_values['max_value'] = ticket_value
                    ticket_values['max_value_display'] = ticket['actual_cost']['display']

                # If the actual ticket value is lower than the actual min value
                if ticket_value < ticket_values['min_value']:
                    ticket_values['min_value'] = ticket_value
                    ticket_values['min_value_display'] = ticket['actual_cost']['display']

        return ticket_values

    def get_context_data(self, **kwargs):
        context = super(ListingPageEventView, self).get_context_data(**kwargs)
        context['organizer'] = get_user_model().objects.get(
            id=self.kwargs['organizer_id'])
        context['event_id'] = self.kwargs['event_id']
        context['event'] = self._get_events(
            context['organizer'],
        )
        context['event']['url'] = context['event']['url'] + '#tickets'
        context['venue'] = self._get_venue(
            context['organizer'],
            context['event']['venue_id'],
        )
        context['tickets'] = self._get_tickets(
            context['organizer'],
            context['event']['id'],
        )
        return context


class GetDiscountView(FormView):
    """ This view allows the user to get a discount """

    template_name = 'buyer/get_discount.html'
    form_class = GetDiscountForm

    def _get_events(self, organizer):
        # Get Event by the id and organizer
        event_in_db = get_object_or_404(
            Event,
            id=self.kwargs['event_id'],
            organizer=organizer,
        )
        """ Get the event from API EB.
            It uses the token of landing page's organizer """
        event = get_event_eb_api(
            get_auth_token(organizer),
            event_in_db.event_id,
        )
        # Add local_date format
        event['start_date'] = parser.parse(event['start']['local'])
        event['end_date'] = parser.parse(event['end']['local'])
        return event

    def post(self, request, *args, **kwargs):
        form = GetDiscountForm(
            request.POST
        )
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return self.url

    def _generate_discount_code(self, member_number, form):
        event = Event.objects.get(
            id=self.kwargs['event_id'])
        organizer = self.get_context_data()['organizer']
        organizer_token = get_auth_token(organizer)
        discount_code = event.event_id + '-' + member_number
        discount = Discount.objects.get(
            event_id=event.id
        )
        eb_event = self.get_context_data()['event']
        #Verify if discount already exists
        discount_code_eb_api = check_discount_code_in_eb(
            organizer_token,
            event.event_id,
            discount_code,
        )

        #If exists
        if len(discount_code_eb_api['discounts']) == 0:
            post_discount_code_to_eb(
                organizer_token,
                event.event_id,
                discount_code,
                discount.value,
            )
            self._generate_url(eb_event, event.event_id, discount_code)
            return True
        else:
            if discount_code_eb_api['discounts'][0]['quantity_sold'] == 0:
                self._generate_url(eb_event, event.event_id, discount_code)
                return True
            else:
                return False

    def _generate_url(self, eb_event, event_id, discount_code):
        self.url = 'https://www.eventbrite.com/e/' + eb_event['id'] + '-tickets-' + event_id + '?discount=' + discount_code + '#tickets'

    def form_valid(self, form):
        if self._generate_discount_code(
            str(form.cleaned_data['member_number']),
            form
        ):
            return JsonResponse({'url':self.url})
        else:
            form.discount_already_used()
            return super(GetDiscountView, self).form_invalid(form)


    def get_context_data(self, **kwargs):
        context = super(GetDiscountView, self).get_context_data(**kwargs)
        context['organizer'] = get_user_model().objects.get(
            id=self.kwargs['organizer_id'])
        context['event_id'] = self.kwargs['event_id']
        context['event'] = self._get_events(
            context['organizer'],
        )
        return context
