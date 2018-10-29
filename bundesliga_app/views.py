from bundesliga_app.models import Event
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from .models import (
    Discount,
    DiscountCode,
    EventTicketType,
)
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
    get_ticket_type,
)
from .forms import (
    DiscountForm,
    GetDiscountForm,
)
from django.views.generic.edit import (
    FormView,
    DeleteView,
)
from django.utils import translation
from django.utils.translation import ugettext as _
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

            """ If the event is free at the moment to load the page it will
            delete the discounts and ticket types in our database"""
            if events[event.id]['is_free']:
                # Search the tickets type of this event
                events_tickets_type = EventTicketType.objects.filter(
                    event=event.id
                )
                for event_ticket_type in events_tickets_type:
                    # For each ticket type,delete the related discounts
                    Discount.objects.filter(
                        ticket_type=event_ticket_type
                    ).delete()
                # Delete tickets type
                events_tickets_type.delete()
            else:
                # If not free, get the tickets types

                # Dictionary for tickets type
                events[event.id]['tickets_type'] = {}
                # Get all tickets type of event from DB
                tickets_type_own = EventTicketType.objects.filter(
                    event=event.id
                )
                # Init has discount in false
                events[event.id]['has_discount'] = False

                for ticket_type_own in tickets_type_own:
                    """ Add ticket_type to dictionary with the id as key
                    and ticket type from API as value """
                    events[event.id]['tickets_type'].update(get_ticket_type(
                        self.request.user,
                        event.event_id,
                        ticket_type_own.id,
                    ))
                    """ Get the discount of the ticket type and
                    add it to the dictionary of ticket_type """
                    # If the ticket type has a discount
                    if Discount.objects.filter(
                            ticket_type=ticket_type_own).exists():
                        # It has a discount, so set in true
                        events[event.id]['has_discount'] = True
                        """ If the ticket is in our DB and
                        its free but has a discount, delete it"""
                        if events[event.id]['tickets_type'][str(
                                ticket_type_own.id)]['free']:
                            Discount.objects.filter(
                                ticket_type=ticket_type_own,
                            ).delete()
                        else:
                            discount = Discount.objects.get(
                                ticket_type=ticket_type_own
                            )

                            events[event.id]['tickets_type'][str(
                                ticket_type_own.id)]['discount'] = discount.__dict__

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

    def _get_event_tickets(self, event_id):
        return get_event_tickets_eb_api(
            get_auth_token(self.request.user),
            event_id,
        )

    # INIT METHODS THAT SUPPORT THE POST OF THIS VIEW
    def _get_events_selected_id(self):
        """ This method get the selected ids from the request
        and put all this ids in an array
        """
        request_body_elements = str(self.request.body).split('event_')
        request_body_elements.pop(0)
        events_id = []
        # Put in array all the events id selected
        for event_id in request_body_elements:
            event = event_id.split('=')
            events_id.append(event[0])
        return events_id

    def _delete_unselected_events(self, selected_events_id):
        """ See if had unselected any event active
            and delete every discount and ticket type that has associated
        """

        # Get actives events from DB and put them in an array
        db_selected_ids = []
        for event in Event.objects.filter(
                organizer=self.request.user).filter(is_active=True):

            db_selected_ids.append(event.event_id)

        # For each selected id
        for db_event_id in db_selected_ids:
            """ If the event its not selected change as no active event
            """
            if db_event_id not in selected_events_id:
                event_in_db = Event.objects.filter(
                    event_id=db_event_id)
                event_in_db.update(is_active=False)
                event_in_db = event_in_db.get()
                # Get the tickets type of that event
                event_tickets_type = EventTicketType.objects.filter(
                    event=event_in_db
                )
                """ For each tycket type
                delete the discount if exists and delete the ticket type
                """
                for ticket_type in event_tickets_type:
                    ticket_type_discounts = Discount.objects.filter(
                        ticket_type=ticket_type
                    )
                    if ticket_type_discounts:
                        Discount.objects.filter(
                            ticket_type=ticket_type
                        ).delete()
                    ticket_type_discounts.delete()

    def _create_event(self, event_in_api_id):
        """
        Create the event with the tickets type from EB
        """
        created_event = Event.objects.create(
            event_id=event_in_api_id,
            organizer=self.request.user,
            is_active=True,
        )
        # Extract the tickets id from EB
        tickets_id_eb = []
        # Search the tickets of the event of EB and save it in db
        tickets = self._get_event_tickets(event_in_api_id)
        for ticket in tickets:
            tickets_id_eb.append(ticket['id'])
            EventTicketType.objects.create(
                event=created_event,
                ticket_id_eb=ticket['id'],
            )

        return tickets_id_eb

    def _update_event(self, event_in_api_id):
        """
        Update the event with the tickets type from EB,
        and returns the tickets id of eb which have been added
        """
        # Get the event and update it as an active event
        event = Event.objects.filter(event_id=event_in_api_id)
        event.update(
            event_id=event_in_api_id,
            organizer=self.request.user,
            is_active=True,
        )

        # Update tickets of event
        # Search the tickets in EB of the event and save it in db
        tickets = self._get_event_tickets(event_in_api_id)
        # Extract the tickets id from EB
        tickets_id_eb = []
        for ticket in tickets:
            tickets_id_eb.append(ticket['id'])
            # If the ticket is not in our DB yet, add it
            if not EventTicketType.objects.filter(
                ticket_id_eb=ticket['id'],
            ).exists():
                EventTicketType.objects.create(
                    event=event.get(),
                    ticket_id_eb=ticket['id'],
                )
            else:
                """ If the ticket is in our DB and
             its free but has a discount, delete it"""
                event_ticket_type = EventTicketType.objects.filter(
                    ticket_id_eb=ticket['id'],
                )
                if ticket['free'] and Discount.objects.filter(
                    ticket_type=event_ticket_type,
                ).exists():
                    Discount.objects.filter(
                        ticket_type=event_ticket_type,
                    ).delete()

        return tickets_id_eb

    def _delete_old_tickets_types(self, tickets_id_eb):
        """
        Verify if exists a ticket type in our db that does not
        exists anymore in EB, and delete it with its discount
        """

        # Get all the EventTicketType from db
        tickets_type_in_db = EventTicketType.objects.all()
        for ticket_type_in_db in tickets_type_in_db:
            """ Verify if the ticket in db,
            is not anymore in eb and delete it with its discount
            """
            if ticket_type_in_db.ticket_id_eb not in tickets_id_eb:
                event_ticket_type = EventTicketType.objects.get(
                    ticket_id_eb=ticket_type_in_db.ticket_id_eb
                )
                # If the ticket type has a discount, delete it
                if Discount.objects.filter(
                    ticket_type=event_ticket_type,
                ).exists():
                    Discount.objects.get(
                        ticket_type=event_ticket_type
                    ).delete()
                # Delete event ticket type
                event_ticket_type.delete()

    # END METHODS THAT SUPPORT THE POST OF THIS VIEW

    def post(self, *args, **kwargs):

        events = self._get_event()
        events_id = self._get_events_selected_id()

        self._delete_unselected_events(events_id)

        tickets_id_eb = []
        # For each event in the api, verify if the selected ones are corrects
        for event_in_api in events:

            # If the event id is an event of organizer
            if event_in_api['id'] in events_id:
                # Verify if this event already exist
                if not Event.objects.filter(
                        event_id=event_in_api['id']).exists():
                    # The event isnt in the BD,create with its tickets type
                    tickets_id_eb.extend(
                        self._create_event(event_in_api['id'])
                    )

                else:
                    """ The event is in the BD, so update the info of event
                    and add the list of tickets id of eb in tickets_id_eb"""
                    tickets_id_eb.extend(
                        self._update_event(event_in_api['id'])
                    )

        self._delete_old_tickets_types(tickets_id_eb)

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

    def _get_tickets_type(self, event):
        # Get the tickets type of EB
        tickets_eb = get_event_tickets_eb_api(
            get_auth_token(self.request.user),
            event.event_id,
        )
        tickets_type = {}
        for ticket_eb in tickets_eb:
            # If the ticket type exists in our db
            if EventTicketType.objects.filter(
                    ticket_id_eb=ticket_eb['id']).exists():

                event_ticket_type = EventTicketType.objects.get(
                    ticket_id_eb=ticket_eb['id'])
                tickets_type[str(event_ticket_type.id)] = ticket_eb

                # If it has a discount
                if Discount.objects.filter(
                        ticket_type=event_ticket_type).exists():
                    discount = Discount.objects.get(
                        ticket_type=event_ticket_type
                    )
                    # If its free, delete the discount
                    if ticket_eb['free']:
                        discount.delete()
                    else:
                        tickets_type[str(event_ticket_type.id)
                                     ]['discount'] = discount.__dict__

            else:
                # Create ticket type
                event_ticket_type = EventTicketType.objects.create(
                    ticket_id_eb=ticket_eb['id'],
                    event=event,
                )
                tickets_type[str(event_ticket_type.id)] = ticket_eb
        # Delete the tickets type that are not in EB
        event_tickets_type_own = EventTicketType.objects.filter(
            event=event)
        for event_ticket_type_own in event_tickets_type_own:
            if str(event_ticket_type_own.id) not in tickets_type.keys():
                Discount.objects.filter(
                    ticket_type=event_ticket_type_own).delete()
                event_ticket_type_own.delete()

        return tickets_type

    def get_context_data(self, **kwargs):
        context = super(EventDiscountsView, self).get_context_data(**kwargs)
        # Get event by id in kwargs
        context['event'] = self.get_event()
        # Get event name in EB API
        context['event_id'] = self.kwargs['event_id']
        context['tickets_type'] = self._get_tickets_type(context['event'])
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
        kwargs['ticket_type_id'] = self.kwargs['ticket_type_id']
        kwargs['event_id'] = self.kwargs['event_id']
        kwargs['user'] = self.request.user

        return kwargs

    def post(self, request, *args, **kwargs):
        if 'discount_id' in self.kwargs:
            discount_id = self.kwargs['discount_id']
        else:
            discount_id = None
        form = DiscountForm(
            request.POST,
            user=request.user,
            event_id=self.kwargs['event_id'],
            ticket_type_id=self.kwargs['ticket_type_id'],
            discount_id=discount_id,
        )

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        ticket_type = EventTicketType.objects.get(
            id=self.kwargs['ticket_type_id']
        )
        self.add_discount(form, ticket_type)
        return HttpResponseRedirect(
            reverse(
                'events_discount',
                kwargs={
                    'event_id': self.get_event().id
                },
            )
        )

    def add_discount(self, form, ticket_type):
        if not ('discount_id' in self.kwargs):
            Discount.objects.create(
                name=form['discount_name'].value(),
                ticket_type=ticket_type,
                value=form['discount_value'].value(),
                value_type='percentage',
            )
        else:
            Discount.objects.filter(pk=self.kwargs['discount_id']).update(
                name=form['discount_name'].value(),
                ticket_type=ticket_type,
                value=form['discount_value'].value(),
                value_type='percentage',
            )

    def get_context_data(self, **kwargs):
        context = super(ManageDiscount, self).get_context_data(**kwargs)
        context['event'] = self.get_event()
        context['ticket_type'] = get_ticket_type(
            self.request.user,
            context['event'].event_id,
            self.kwargs['ticket_type_id'],
        )
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
        return self.get_discount()

    def get_context_data(self, **kwargs):
        context = super(DeleteDiscountView, self).get_context_data(**kwargs)
        context['event'] = self.get_event()
        return context


""" -- Buyer Views -- """


class LandingPageBuyerView(TemplateView):
    """ This is the landing page of an organizer for the buyer """

    template_name = 'buyer/landing_page_buyer.html'

    # Get all the data of organizer'events from EB API
    def _get_events(self, organizer):
        # Dictionary for events
        events = {}
        # Get all active events from DB
        events_own = Event.objects.filter(
            organizer=organizer).filter(is_active=True)
        for event in events_own:
            """ Add event to dictionary with the id as key
            and event from API as value """
            events[event.id] = get_event_eb_api(
                get_auth_token(organizer),
                event.event_id,
            )
            # Add local_date format
            events[event.id]['start_date'] = parser.parse(
                events[event.id]['start']['local'])
            events[event.id]['end_date'] = parser.parse(
                events[event.id]['end']['local'])

            # Dictionary for tickets type
            events[event.id]['tickets_type'] = {}
            # Get all tickets type of event from DB
            tickets_type_own = EventTicketType.objects.filter(
                event=event.id
            )
            for ticket_type_own in tickets_type_own:
                """ Add ticket_type to dictionary with the id as key
                and ticket type from API as value """
                events[event.id]['tickets_type'].update(get_ticket_type(
                    organizer,
                    event.event_id,
                    ticket_type_own.id,
                ))
                """ Get the discount of the ticket type and
                add it to the dictionary of ticket_type """
                # If the ticket type has a discount
                if Discount.objects.filter(
                        ticket_type=ticket_type_own.id).exists():

                    discount = Discount.objects.get(
                        ticket_type=ticket_type_own.id
                    )

                    events[event.id]['tickets_type'][str(
                        ticket_type_own.id)]['discount'] = discount.__dict__
                    """ If the event is free at the moment to load the page it will
                    delete the discounts and ticket types in our database"""
                    if events[event.id]['is_free']:
                        # Search the tickets type of this event
                        events_tickets_type = EventTicketType.objects.filter(
                            event=event.id
                        )
                        for event_ticket_type in events_tickets_type:
                            # For each ticket type,delete the related discounts
                            Discount.objects.filter(
                                ticket_type=event_ticket_type
                            ).delete()
                        # Delete tickets type
                        events_tickets_type.delete()

        return events

    def get_context_data(self, **kwargs):
        context = super(LandingPageBuyerView, self).get_context_data(**kwargs)
        context['organizer'] = get_user_model().objects.get(
            id=self.kwargs['organizer_id'])
        context['events'] = self._get_events(
            context['organizer']
        )
        return context


class ListingPageEventView(FormView):
    """ This view visualize the info of an event """
    template_name = 'buyer/listing_page_event.html'
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

    def _get_tickets_type(self, event_id):
        event = Event.objects.get(id=event_id)
        tickets_type_in_db = EventTicketType.objects.filter(
            event=event
        )
        tickets_type = {}
        for ticket_type_in_db in tickets_type_in_db:
            tickets_type.update(get_ticket_type(
                self.request.user,
                event.event_id,
                ticket_type_in_db.id,
            ))
            if Discount.objects.filter(ticket_type=ticket_type_in_db).exists():
                discount = Discount.objects.get(
                    ticket_type=ticket_type_in_db
                )
                tickets_type[str(ticket_type_in_db.id)
                             ]['discount'] = discount.__dict__
        return tickets_type

    def _get_discounts(self, tickets_type):
        discounts = []

        for ticket_id in tickets_type.keys():
            if Discount.objects.filter(ticket_type=ticket_id).exists():
                discounts.append(Discount.objects.get(
                    ticket_type=ticket_id).__dict__)
        return discounts

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

    def get_success_url(self):
        return self.url

    def _generate_discount_code(self, form):
        event = Event.objects.get(
            id=self.kwargs['event_id'])
        organizer = self.get_context_data()['organizer']
        organizer_token = get_auth_token(organizer)
        discount_code = event.event_id + '-'
        member_numbers = []
        for i in range(1, len(form.cleaned_data)):
            member_numbers.append(
                str(form.cleaned_data['member_number_{}'.format(i)]))
        discount_code += '_'.join(member_numbers)
        # Find ticket type
        ticket_type = EventTicketType.objects.get(
            id=form.cleaned_data['tickets_type']
        )
        # Find discount
        discount = Discount.objects.get(
            ticket_type=ticket_type
        )
        eb_event = self.get_context_data()['event']
        # Verify if discount already exists
        discount_code_eb_api = check_discount_code_in_eb(
            organizer_token,
            event.event_id,
            discount_code,
        )

        # for number in range(1, len(form.cleaned_data) + 1):
        #     discount_code_local = DiscountCode.objects.filter(
        #         event=event,
        #     ).filter(
        #         member_number=form.cleaned_data[
        #             'member_number_{}'.format(number)
        #         ])

        # If exists
        if len(discount_code_eb_api['discounts']) == 0:
            post_discount_code_to_eb(
                organizer_token,
                event.event_id,
                discount_code,
                discount.value,
                ticket_type.ticket_id_eb,
                uses=len(form.cleaned_data) - 1,
            )
            DiscountCode.objects.create(
                member_number=form.cleaned_data['member_number_1'],
                discount=discount,
                eb_event_id=eb_event['id'],
                discount_code=discount_code,
            )
            self._generate_url(eb_event, event.event_id, discount_code)
            return True
        else:
            quantity_available = discount_code_eb_api['discounts'][0]['quantity_available']
            quantity_sold = discount_code_eb_api['discounts'][0]['quantity_sold']
            if quantity_available - quantity_sold == 0:
                return False
            else:
                self._generate_url(eb_event, event.event_id, discount_code)
                return True

    def _generate_url(self, eb_event, event_id, discount_code):
        self.url = 'https://www.eventbrite.com/e/' + \
            eb_event['id'] + '-tickets-' + event_id + \
            '?discount=' + discount_code + '#tickets'

    def form_valid(self, form):
        if self._generate_discount_code(
            form
        ):
            return JsonResponse({'url': self.url})
        else:
            form.discount_already_used()
            return super(ListingPageEventView, self).form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super(ListingPageEventView, self).get_form_kwargs()
        kwargs['event_id'] = self.kwargs['event_id']
        kwargs['user'] = self.kwargs['organizer_id']

        return kwargs

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
        context['tickets_type'] = self._get_tickets_type(context['event_id'])
        context['discounts'] = self._get_discounts(context['tickets_type'])
        context['tickets'] = self._get_tickets(
            context['organizer'],
            context['event']['id'],
        )
        return context


""" -- tranlation View -- """


class ActivateLanguageView(View):
    language_code = ''
    redirect_to = ''

    def get(self, request, *args, **kwargs):
        self.redirect_to = request.META.get('HTTP_REFERER')
        self.language_code = kwargs.get('language_code')
        translation.activate(self.language_code)
        request.session[translation.LANGUAGE_SESSION_KEY] = self.language_code
        return redirect(self.redirect_to)
