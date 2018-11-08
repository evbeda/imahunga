from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView, View
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.http import (
    HttpResponseRedirect,
    JsonResponse,
)
from .models import (
    Discount,
    DiscountCode,
    DiscountType,
    Event,
    EventDiscount,
    EventTicketType,
    MemberDiscountCode,
    StatusMemberDiscountCode,
    TicketTypeDiscount,
)
from .utils import (
    EventAccessMixin,
    DiscountAccessMixin,
    check_discount_code_in_eb,
    delete_discount_code_from_eb,
    get_auth_token,
    get_event_eb_api,
    get_events_user_eb_api,
    get_ticket_type,
    get_user_eb_api,
    get_venue_eb_api,
    get_event_tickets_eb_api,
    post_event_discount_code_to_eb,
    post_ticket_discount_code_to_eb,
    update_discount_code_to_eb,
)
from .forms import (
    DiscountTicketForm,
    DiscountEventForm,
    GetDiscountForm,
)
from django.views.generic.edit import (
    DeleteView,
    FormView,
)
from django.utils import translation
from django.utils.translation import ugettext as _
from django.contrib.auth import get_user_model
from dateutil import parser
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)


@method_decorator(login_required, name='dispatch')
class HomeView(ListView, LoginRequiredMixin):

    """ This is the home view.
    Here we show all the events of the user in our app """

    template_name = 'index.html'
    model = Event
    context_object_name = 'own_events'
    paginate_by = 5

    def get_queryset(self):
        return Event.objects.filter(
            organizer=self.request.user,
        ).filter(is_active=True)

    def _get_events(self, own_events):
        """ Get all the data of organizer events from EB API
        Also, each event has their tickets type and
        a boolean with the info about their discounts"""

        events = {}

        for event in own_events:
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
                    TicketTypeDiscount.objects.filter(
                        ticket_type=event_ticket_type
                    ).delete()
                # Delete tickets type
                events_tickets_type.delete()
            else:
                # If not free, set the tickets types
                events[event.id]['has_discount'] = False

                # If has a event discount, set has discount in true
                if EventDiscount.objects.filter(
                        event=event).exists():
                        events[event.id]['has_discount'] = True

                self._set_tickets_type(events[event.id], event)
        return events

    def _set_tickets_type(self, event_api, event_own):
        """ Receive 2 params:
        - event_api: The dict with the event info for context data
        - event_own: The event of our DB
        This method set all the tickets type of the event with its discount
        If the ticket type its free and has a discount, delete it"""

        event_api['tickets_type'] = {}

        tickets_type_own = EventTicketType.objects.filter(
            event=event_own
        )

        for ticket_type_own in tickets_type_own:
            """ Add ticket_type to dictionary with the id as key
            and ticket type from API as value """
            event_api['tickets_type'].update(get_ticket_type(
                self.request.user,
                event_own.event_id,
                ticket_type_own.id,
            ))

            if TicketTypeDiscount.objects.filter(
                    ticket_type=ticket_type_own).exists():

                event_api['has_discount'] = True

                if event_api['tickets_type'][str(
                        ticket_type_own.id)]['free']:
                    TicketTypeDiscount.objects.filter(
                        ticket_type=ticket_type_own,
                    ).delete()
                else:
                    discount = TicketTypeDiscount.objects.get(
                        ticket_type=ticket_type_own
                    )
                    event_api['tickets_type'][str(
                        ticket_type_own.id)]['discount'] = discount.__dict__

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['events'] = self._get_events(context['own_events'])
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

        for db_event_id in db_selected_ids:
            """ If the event its not selected change as no active event
            """
            if db_event_id not in selected_events_id:
                event_in_db = Event.objects.filter(
                    event_id=db_event_id)
                event_in_db.update(is_active=False)
                event_in_db = event_in_db.get()

                event_tickets_type = EventTicketType.objects.filter(
                    event=event_in_db
                )

                # Delete the event discount if exists
                if EventDiscount.objects.filter(
                        event=event_in_db):
                    EventDiscount.objects.filter(
                        event=event_in_db
                    ).delete()

                """ For each tycket type
                delete the discount if exists and delete the ticket type
                """
                for ticket_type in event_tickets_type:
                    ticket_type_discounts = TicketTypeDiscount.objects.filter(
                        ticket_type=ticket_type
                    )
                    if ticket_type_discounts:
                        TicketTypeDiscount.objects.filter(
                            ticket_type=ticket_type
                        ).delete()
                    ticket_type.delete()

    def _create_event(self, event_in_api_id):
        """ Create the event with the tickets type from EB """

        created_event = Event.objects.create(
            event_id=event_in_api_id,
            organizer=self.request.user,
            is_active=True,
        )

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
        """ Update the event with the tickets type from EB,
            also delete the discounts of a free ticket type
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
        tickets_id_eb = self._update_tickets(event_in_api_id, event)

        return tickets_id_eb

    def _update_tickets(self, event_in_api_id, event):
        """ Search the tickets in EB, create if are not in DB yet,
            and if is in the DB and the ticket is free, delete it discount
            It returns the id of tickets type from eB
        """

        tickets = self._get_event_tickets(event_in_api_id)

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
                if ticket['free'] and TicketTypeDiscount.objects.filter(
                    ticket_type=event_ticket_type,
                ).exists():
                    TicketTypeDiscount.objects.filter(
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
                if TicketTypeDiscount.objects.filter(
                    ticket_type=event_ticket_type,
                ).exists():
                    TicketTypeDiscount.objects.get(
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
        for event_in_api in events:

            if event_in_api['id'] in events_id:
                # Verify if this event already exist
                if not Event.objects.filter(
                        event_id=event_in_api['id']).exists():
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
        context['events'] = self._get_event()
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
        """ Get the tickets type of EB and
        - If is not in our DB, create it
        - If is in our DB:
            - If its free, delete it discount
            - If not free, get the discount
        - If a ticket is in our DB but no in EB, delete it """

        tickets_eb = get_event_tickets_eb_api(
            get_auth_token(self.request.user),
            event.event_id,
        )
        tickets_type = {}
        for ticket_eb in tickets_eb:
            if EventTicketType.objects.filter(
                    ticket_id_eb=ticket_eb['id']).exists():

                event_ticket_type = EventTicketType.objects.get(
                    ticket_id_eb=ticket_eb['id'])
                tickets_type[str(event_ticket_type.id)] = ticket_eb

                if TicketTypeDiscount.objects.filter(
                        ticket_type=event_ticket_type).exists():
                    discount = TicketTypeDiscount.objects.get(
                        ticket_type=event_ticket_type
                    )

                    if ticket_eb['free']:
                        discount.delete()
                    else:
                        tickets_type[str(event_ticket_type.id)
                                     ]['discount'] = discount.__dict__

            else:

                event_ticket_type = EventTicketType.objects.create(
                    ticket_id_eb=ticket_eb['id'],
                    event=event,
                )
                tickets_type[str(event_ticket_type.id)] = ticket_eb
        self._delete_old_tickets_types(event, tickets_type)

        return tickets_type

    def _delete_old_tickets_types(self, event, tickets_type):
        """ Delete the tickets type that are not in EB """

        event_tickets_type_own = EventTicketType.objects.filter(
            event=event)
        for event_ticket_type_own in event_tickets_type_own:
            if str(event_ticket_type_own.id) not in tickets_type.keys():
                TicketTypeDiscount.objects.filter(
                    ticket_type=event_ticket_type_own).delete()
                event_ticket_type_own.delete()

    def _get_discount_event(self, event):
        """ Get the event discount if exists"""

        if EventDiscount.objects.filter(event=event).exists():
            return EventDiscount.objects.filter(
                event=event
            ).get()

    def _verify_discount(self, event_discount, tickets_type):
        """ This method will return what type of discount the event has """

        if event_discount:
            return 'Event'
        for ticket_id, ticket in tickets_type.items():
            if 'discount' in ticket:
                return 'Ticket'
        return None

    def get_context_data(self, **kwargs):
        context = super(EventDiscountsView, self).get_context_data(**kwargs)
        context['event'] = self.get_event()
        context['event_id'] = self.kwargs['event_id']
        context['event_discount'] = self._get_discount_event(
            context['event']
        )
        context['tickets_type'] = self._get_tickets_type(context['event'])
        context['has_discount'] = self._verify_discount(
            context['event_discount'],
            context['tickets_type'],
        )
        context['event_name'] = get_event_eb_api(
            get_auth_token(self.request.user),
            context['event'].event_id,
        )['name']['text']
        return context


@method_decorator(login_required, name='dispatch')
class ManageDiscountEvent(FormView, LoginRequiredMixin, DiscountAccessMixin):

    """ This is the the Manage Discount Event view,
    here the organizer can create or modify a event discount """

    form_class = DiscountEventForm
    template_name = 'organizer/create_discount_event.html'

    def get_form_kwargs(self):
        kwargs = super(ManageDiscountEvent, self).get_form_kwargs()
        if 'discount_id' in self.kwargs:
            discount = self.get_discount()
            if discount:
                kwargs['initial']['discount_name'] = discount.name
                kwargs['initial']['discount_type'] = discount.value_type
                kwargs['initial']['discount_value'] = discount.value
        kwargs['event_id'] = self.kwargs['event_id']
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if 'discount_id' in self.kwargs:
            discount_id = self.kwargs['discount_id']
        else:
            discount_id = None
        form = DiscountEventForm(
            request.POST,
            user=request.user,
            event_id=self.kwargs['event_id'],
            discount_id=discount_id,
        )

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.delete_discount_ticket_type(self.get_event())
        self.add_discount(form, self.get_event())
        return HttpResponseRedirect(
            reverse(
                'events_discount',
                kwargs={
                    'event_id': self.get_event().id
                },
            )
        )

    def delete_discount_ticket_type(self, event):
        """ Delete ticket discounts if exists """

        tickets_type = EventTicketType.objects.filter(
            event=event,
        )
        for ticket_type in tickets_type:
            if TicketTypeDiscount.objects.filter(
                    ticket_type=ticket_type).exists():
                TicketTypeDiscount.objects.filter(
                    ticket_type=ticket_type).delete()

    def add_discount(self, form, event):
        """ Create or update the event discount according to the case """

        discount_type = DiscountType.objects.filter(
            name="Event"
        ).get()
        if not ('discount_id' in self.kwargs):
            EventDiscount.objects.create(
                name=form['discount_name'].value(),
                event=event,
                discount_type=discount_type,
                value=form['discount_value'].value(),
                value_type='percentage',
            )
        else:
            EventDiscount.objects.filter(pk=self.kwargs['discount_id']).update(
                name=form['discount_name'].value(),
                event=event,
                discount_type=discount_type,
                value=form['discount_value'].value(),
                value_type='percentage',
            )

    def _verify_discount_ticket_type(self, event):
        """ Search if exists a ticket discount """

        has_discount_ticket_type = False
        tickets_type = EventTicketType.objects.filter(
            event=event,
        )
        for ticket_type in tickets_type:
            if TicketTypeDiscount.objects.filter(
                    ticket_type=ticket_type).exists():
                has_discount_ticket_type = True
        return has_discount_ticket_type

    def get_context_data(self, **kwargs):
        context = super(ManageDiscountEvent, self).get_context_data(**kwargs)
        context['event'] = self.get_event()
        context['has_discount_ticket_type'] = self._verify_discount_ticket_type(
            context['event']
        )
        if 'discount_id' in self.kwargs:
            context['discount'] = get_object_or_404(
                Discount,
                id=self.kwargs['discount_id'],
            )
        return context


@method_decorator(login_required, name='dispatch')
class ManageDiscountTicketType(FormView, LoginRequiredMixin, DiscountAccessMixin):

    """ This is the the Manage Discount Discount view,
    here the organizer can create or modify a ticket discount """

    form_class = DiscountTicketForm
    template_name = 'organizer/create_discount_ticket_type.html'

    def get_form_kwargs(self):
        kwargs = super(ManageDiscountTicketType, self).get_form_kwargs()
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
        form = DiscountTicketForm(
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
        self.delete_discount_event(self.get_event())
        self.add_discount(form, ticket_type)
        return HttpResponseRedirect(
            reverse(
                'events_discount',
                kwargs={
                    'event_id': self.get_event().id
                },
            )
        )

    def delete_discount_event(self, event):
        """ Delete ticket discounts if exists """

        if EventDiscount.objects.filter(event=event).exists():
            EventDiscount.objects.filter(
                event=event).delete()

    def add_discount(self, form, ticket_type):
        """ Create or update the ticket discount according to the case """

        discount_type = DiscountType.objects.filter(
            name="Ticket Type"
        ).get()
        if not ('discount_id' in self.kwargs):
            TicketTypeDiscount.objects.create(
                name=form['discount_name'].value(),
                ticket_type=ticket_type,
                discount_type=discount_type,
                value=form['discount_value'].value(),
                value_type='percentage',
            )
        else:
            TicketTypeDiscount.objects.filter(
                pk=self.kwargs['discount_id']).update(
                    name=form['discount_name'].value(),
                    ticket_type=ticket_type,
                    discount_type=discount_type,
                    value=form['discount_value'].value(),
                    value_type='percentage',
            )

    def _verify_discount_event(self, event):
        """ Search if exists a event discount """

        has_discount_event = False
        if EventDiscount.objects.filter(event=event).exists():
            has_discount_event = True
        return has_discount_event

    def get_context_data(self, **kwargs):
        context = super(ManageDiscountTicketType, self).get_context_data(**kwargs)
        context['event'] = self.get_event()
        context['has_discount_event'] = self._verify_discount_event(
            context['event']
        )
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

class LandingPageBuyerView(ListView):

    """ This is the landing page of an organizer for the buyer
    here the buyer can visualize the events with its discounts """

    template_name = 'buyer/landing_page_buyer.html'
    model = Event
    context_object_name = 'own_events'
    paginate_by = 6

    def get_queryset(self):
        organizer = get_user_model().objects.get(
            id=self.kwargs['organizer_id'])
        return Event.objects.filter(
            organizer=organizer).filter(is_active=True)

    def _get_events(self, organizer, events_own):
        """ Get all the data of organizer events from EB API
        Also, each event has their tickets type and
         the info about their discounts"""

        events = {}

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

            events[event.id]['tickets_type'] = {}
            # Get all tickets type of event from DB
            tickets_type_own = EventTicketType.objects.filter(
                event=event.id
            )
            events[event.id]['max_discount'] = 0
            events[event.id]['min_discount'] = 0
            events[event.id]['discounts'] = {}

            if EventDiscount.objects.filter(
                    event=event).exists():
                self._set_event_discount(events[event.id], event)

            for ticket_type_own in tickets_type_own:

                if TicketTypeDiscount.objects.filter(
                        ticket_type=ticket_type_own.id).exists():

                    self._set_ticket_type_discount(
                        events[event.id],
                        ticket_type_own,
                    )

            if events[event.id]['is_free']:
                self._delete_free_event_discounts(event.id)

        return events

    def _set_event_discount(self, event, event_own):
        """ Set the value of discount according the event discount """

        discount = EventDiscount.objects.get(
            event=event_own,
        )
        event['max_discount'] = discount.value
        event['min_discount'] = discount.value
        event['discounts'][discount.id] = discount.__dict__

    def _set_ticket_type_discount(self, event, ticket_type_own):
        """ Set the value of discount according the ticket discount """

        discount = TicketTypeDiscount.objects.get(
            ticket_type=ticket_type_own.id
        )
        event['discounts'][discount.id] = discount.__dict__

        if discount.value > event['max_discount']:
            event['max_discount'] = discount.value

        if event['min_discount'] == 0:
            event['min_discount'] = discount.value

        if discount.value < event['min_discount']:
            event['min_discount'] = discount.value

    def _delete_free_event_discounts(self, event_id):
        """ If the event is free at the moment to load the page it will
        delete the discounts and ticket types in our database"""

        EventDiscount.objects.filter(event=event_id).delete()

        events_tickets_type = EventTicketType.objects.filter(
            event=event_id
        )

        for event_ticket_type in events_tickets_type:
            # For each ticket type,delete the related discounts
            TicketTypeDiscount.objects.filter(
                ticket_type=event_ticket_type
            ).delete()
        # Delete tickets type
        events_tickets_type.delete()

    def get_context_data(self, **kwargs):
        context = super(LandingPageBuyerView, self).get_context_data(**kwargs)
        context['organizer'] = get_user_model().objects.get(
            id=self.kwargs['organizer_id'])
        context['events'] = self._get_events(
            context['organizer'],
            context['own_events']
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

    def _get_tickets_type(self, event_id, organizer):
        event = Event.objects.get(id=event_id)
        tickets_type_in_db = EventTicketType.objects.filter(
            event=event
        )
        tickets_type = {}
        for ticket_type_in_db in tickets_type_in_db:
            tickets_type.update(get_ticket_type(
                organizer,
                event.event_id,
                ticket_type_in_db.id,
            ))
            if TicketTypeDiscount.objects.filter(
                    ticket_type=ticket_type_in_db).exists():
                discount = TicketTypeDiscount.objects.get(
                    ticket_type=ticket_type_in_db
                )
                tickets_type[str(ticket_type_in_db.id)
                             ]['discount'] = discount.__dict__

        return tickets_type

    def _get_tickets_discounts(self, tickets_type):
        discounts = {
            'max_discount': 0,
            'min_discount': 0,
            'available': False,
        }

        for ticket_id in tickets_type.keys():
            if TicketTypeDiscount.objects.filter(
                    ticket_type=ticket_id).exists():
                discount = TicketTypeDiscount.objects.get(
                    ticket_type=ticket_id)
                discounts['available'] = True
                if discount.value > discounts['max_discount']:
                        discounts['max_discount'] = discount.value

                if discounts['min_discount'] == 0:
                        discounts['min_discount'] = discount.value

                if discount.value < discounts['min_discount']:
                        discounts['min_discount'] = discount.value
        return discounts


    def _get_tickets(self, tickets):
        ticket_values = {
            'min_value': None,
            'min_value_display': None,
            'max_value': None,
            'max_value_display': None,
        }
        for ticket_id, ticket in tickets.items():

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

    def _get_event_discount(self, event_id):
        event_discount = {
            'value': 0,
            'available': False,
        }
        event = Event.objects.get(
            id=event_id
        )
        if EventDiscount.objects.filter(
            event=event
        ).exists():
            event_discount['value'] = EventDiscount.objects.get(
                event=event
            ).value
            event_discount['available'] = True

        return event_discount

    def _generate_discount_code(self, form):
        event = Event.objects.get(
            id=self.kwargs['event_id'])
        organizer = self.get_context_data()['organizer']
        discount_code = event.event_id + '-'

        if self._verify_member_numbers(form, organizer, event):
            uknown_status = StatusMemberDiscountCode.objects.get(
                name="Unknown"
            )
            if 'tickets_type' in form.cleaned_data.keys():
                iterator = range(1, len(form.cleaned_data))
            else:
                iterator = range(1, len(form.cleaned_data) + 1)
            member_numbers = []

            for i in iterator:
                member_numbers.append(
                    str(form.cleaned_data['member_number_{}'.format(i)]))

            discount_code += '_'.join(member_numbers)

            eb_event = self.get_context_data()['event']

            tickets_discounts = self.get_context_data()['tickets_discounts']
            event_discount = self.get_context_data()['event_discount']
            if tickets_discounts['available']:
                # Find ticket type
                ticket_type = EventTicketType.objects.get(
                    id=form.cleaned_data['tickets_type']
                )
                # Find discount
                discount = TicketTypeDiscount.objects.get(
                    ticket_type=ticket_type
                )
                post_ticket_discount_code_to_eb(
                    organizer,
                    event.event_id,
                    discount_code,
                    discount.value,
                    ticket_type.ticket_id_eb,
                    uses=len(form.cleaned_data) - 1,
                )
            elif event_discount['available']:
                discount = EventDiscount.objects.get(
                    event=event
                )
                post_event_discount_code_to_eb(
                    organizer,
                    event.event_id,
                    discount_code,
                    discount.value,
                    uses=len(form.cleaned_data)
                )
            discount_code_object = DiscountCode.objects.create(
                discount=discount,
                discount_code=discount_code,
            )

            for number in iterator:
                MemberDiscountCode.objects.create(
                    discount_code=discount_code_object,
                    member_number=form.cleaned_data['member_number_{}'.format(
                        number)],
                    status=uknown_status
                )

            self._generate_url(eb_event, event.event_id, discount_code)
            return True
        else:
            return False

    def _verify_member_numbers(self, form, organizer, event):
        uknown_status = StatusMemberDiscountCode.objects.get(
            name="Unknown"
        )
        canceled_status = StatusMemberDiscountCode.objects.get(
            name="Canceled"
        )
        used_status = StatusMemberDiscountCode.objects.get(
            name="Used"
        )
        # for each sent number
        ticket_discount = 'tickets_type' in form.cleaned_data.keys()
        if ticket_discount:
            iterator = range(1, len(form.cleaned_data))
        else:
            iterator = range(1, len(form.cleaned_data) + 1)

        for number in iterator:
            # verify if a discount_code with uknown status exists
            existing_discount_code = MemberDiscountCode.objects.filter(
                member_number=form.cleaned_data[
                    'member_number_{}'.format(number)
                ]).filter(
                    status=uknown_status
            )
            condition = False
            # If exists
            if existing_discount_code:
                for i in range(len(existing_discount_code)):
                    discount_code = DiscountCode.objects.get(
                        id=existing_discount_code[i].discount_code.id
                    )
                    if self.get_context_data()['tickets_discounts']['available']:
                        discount = TicketTypeDiscount.objects.get(
                            id=discount_code.discount.id
                        )
                        ticket_type = EventTicketType.objects.get(
                            id=discount.ticket_type.id
                        )
                        condition = event.id == ticket_type.event.id
                    else:
                        discount = EventDiscount.objects.get(
                            id=discount_code.discount.id
                        )
                        condition = event.id == discount.event_id
                    if condition:
                        # Verify if discount already exists in EB
                        discount_code_eb_api = check_discount_code_in_eb(
                            organizer,
                            event.event_id,
                            discount_code.discount_code,
                        )

                        quantity_available = discount_code_eb_api['discounts'][0]['quantity_available']
                        quantity_sold = discount_code_eb_api['discounts'][0]['quantity_sold']
                        uses_left = quantity_available - quantity_sold

                        # If there aren't any more uses available
                        if uses_left == 0:
                            # Add Error
                            form.add_error('member_number_1',
                                           _('Number {} has already used the discount for this event'.format(
                                               form.cleaned_data[
                                                   'member_number_{}'.format(
                                                       number)
                                               ])))

                            # Set all discounts codes related as used
                            MemberDiscountCode.objects.filter(
                                discount_code=discount_code
                            ).update(
                                status=used_status
                            )
                            return False
                        else:
                            if quantity_sold != 0:
                                # Cancel status for this member's discount
                                canceled_code = MemberDiscountCode.objects.filter(
                                    id=existing_discount_code[i].id
                                )
                                canceled_code.update(
                                    status=canceled_status
                                )

                                # Update uses in EB
                                updated_discount_code = update_discount_code_to_eb(
                                    organizer,
                                    discount_code_eb_api['discounts'][0]['id'],
                                    discount_code_eb_api['discounts'][0]['quantity_available'] - 1
                                )

                                discount_codes_related = MemberDiscountCode.objects.filter(
                                    discount_code=discount_code
                                ).exclude(
                                    member_number=form.cleaned_data[
                                        'member_number_{}'.format(number)]
                                )

                                quantity_available = updated_discount_code['quantity_available']
                                quantity_sold = updated_discount_code['quantity_sold']
                                uses_left = quantity_available - quantity_sold
                                # Update all discounts to used
                                for i in range(len(discount_codes_related)):
                                    discount_code = DiscountCode.objects.get(
                                        id=discount_codes_related[i].discount_code.id
                                    )

                                    if self.get_context_data()['tickets_discounts']['available']:
                                        discount = TicketTypeDiscount.objects.get(
                                            id=discount_code.discount.id
                                        )
                                        ticket_type = EventTicketType.objects.get(
                                            id=discount.ticket_type.id
                                        )
                                        condition = event.id == ticket_type.event.id
                                    else:
                                        discount = EventDiscount.objects.get(
                                            id=discount_code.discount.id
                                        )
                                        condition = event.id == discount.event_id
                                    if condition:
                                        # If there are no more uses
                                        if uses_left == 0:
                                            update_discount = MemberDiscountCode.objects.filter(
                                                id=discount_codes_related[i].id
                                            )
                                            update_discount.update(
                                                status=used_status
                                            )
                                        else:
                                            if quantity_sold != 0:
                                                # Update one discount as used
                                                update_discount = MemberDiscountCode.objects.filter(
                                                    id=discount_codes_related[i].id
                                                )
                                                update_discount.update(
                                                    status=used_status
                                                )
                                            break
                            else:
                                discount_code_id = existing_discount_code[i].discount_code.id
                                if quantity_available == 1:
                                    MemberDiscountCode.objects.filter(
                                        id=existing_discount_code[i].id
                                    ).delete()

                                    DiscountCode.objects.filter(
                                        id=discount_code_id
                                    ).delete()

                                    delete_discount_code_from_eb(
                                        organizer,
                                        discount_code_eb_api['discounts'][0]['id'])
                                else:
                                    MemberDiscountCode.objects.filter(
                                        id=existing_discount_code[i].id
                                    ).update(
                                        status=canceled_status
                                    )
                                    update_discount_code_to_eb(
                                        organizer,
                                        discount_code_eb_api['discounts'][0]['id'],
                                        discount_code_eb_api['discounts'][0]['quantity_available'] - 1
                                    )
                    else:
                        used_discount_code = MemberDiscountCode.objects.filter(
                            member_number=form.cleaned_data[
                                'member_number_{}'.format(number)
                            ]).filter(
                            status=used_status
                        )
                        for i in range(len(used_discount_code)):
                            discount_code = DiscountCode.objects.get(
                                id=used_discount_code[i].discount_code.id
                            )
                            if self.get_context_data()['tickets_discounts']['available']:
                                discount = TicketTypeDiscount.objects.get(
                                    id=discount_code.discount.id
                                )
                                ticket_type = EventTicketType.objects.get(
                                    id=discount.ticket_type.id
                                )
                                condition = event.id == ticket_type.event.id
                            else:
                                discount = EventDiscount.objects.get(
                                    id=discount_code.discount.id
                                )
                                condition = event.id == discount.event_id

                            if condition:
                                form.add_error('member_number_1',
                                           _('Number {} has already used the discount for this event'.format(
                                               form.cleaned_data[
                                                   'member_number_{}'.format(
                                                       number)
                                               ])))
                                return False

            else:
                used_discount_code = MemberDiscountCode.objects.filter(
                    member_number=form.cleaned_data[
                        'member_number_{}'.format(number)
                    ]).filter(
                        status=used_status
                )
                if used_discount_code:
                    for i in range(len(used_discount_code)):
                        discount_code = DiscountCode.objects.get(
                            id=used_discount_code[i].discount_code.id
                        )
                        if self.get_context_data()['tickets_discounts']['available']:
                            discount = TicketTypeDiscount.objects.get(
                                id=discount_code.discount.id
                            )
                            ticket_type = EventTicketType.objects.get(
                                id=discount.ticket_type.id
                            )
                            condition = event.id == ticket_type.event.id
                        else:
                            discount = EventDiscount.objects.get(
                                id=discount_code.discount.id
                            )
                            condition = event.id == discount.event_id

                        if condition:
                            form.add_error('member_number_1',
                                           _('Number {} has already used the discount for this event'.format(
                                               form.cleaned_data[
                                                   'member_number_{}'.format(
                                                       number)
                                               ])))
                            return False
            if 'tickets_type' in form.cleaned_data.keys():
                if number == len(form.cleaned_data) - 1:
                    return True
            else:
                if number == len(form.cleaned_data):
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
        context['tickets_type'] = self._get_tickets_type(
            context['event_id'],
            context['organizer'],
        )
        context['tickets_discounts'] = self._get_tickets_discounts(context['tickets_type'])
        context['event_discount'] = self._get_event_discount(context['event_id'])
        context['tickets_value'] = self._get_tickets(
            context['tickets_type']
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
