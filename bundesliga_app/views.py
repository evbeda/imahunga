from bundesliga_app.models import Event
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from django.contrib import messages
from eventbrite import Eventbrite
from .models import Discount
from .utils import (
    get_auth_token,
    get_local_date,
    get_event_eb_api,
    get_events_user_eb_api,
)
from .forms import DiscountForm
from django.views.generic.edit import FormView
from django.forms.utils import ErrorList


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
            events[event.id]['local_date'] = get_local_date(
                events[event.id]
            )
            # Add discount of the event
            discount = Discount.objects.filter(
                event=event.id
            )
            if discount:
                events[event.id]['discount'] = discount.get().value
                events[event.id]['discount_type'] = discount.get().value_type
        return events

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['events'] = self._get_events()

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
        # See if had unselected any event active
        db_selected_ids = []
        for event in Event.objects.filter(organizer=self.request.user).filter(is_active=True):
            db_selected_ids.append(event.event_id)
        for db_event_id in db_selected_ids:
            if db_event_id not in events_id:
                Event.objects.filter(
                    event_id=db_event_id).update(is_active=False)
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
        eventbrite = Eventbrite(
            get_auth_token(self.request.user),
        )
        context['me'] = eventbrite.get('/users/me/')
        context['already_selected_id'] = []
        for event in Event.objects.filter(organizer=self.request.user).filter(is_active=True):
            context['already_selected_id'].append(event.event_id)
        # Bring live events of user
        context['events'] = self._get_event()
        for event in context['events']:
            event['local_date'] = get_local_date(event)
        return context


@method_decorator(login_required, name='dispatch')
class EventDiscountsView(TemplateView, LoginRequiredMixin):

    """ This is the the Event Discounts view,
    here the organizer can manage the discounts of the event"""

    template_name = 'organizer/event_discounts.html'

    def get(self, request, *args, **kwargs):
        # import ipdb;ipdb.set_trace()
        if len(self.get_context_data()['event']) == 0:
            return HttpResponseRedirect(
                reverse(
                    'invalid_access'
                )
            )
        return super(EventDiscountsView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EventDiscountsView, self).get_context_data(**kwargs)
        # Get event by id in kwargs
        context['event'] = Event.objects.filter(
            id=self.kwargs['event_id']
        ).filter(
            organizer=self.request.user
        )
        if len(context['event']) > 0:
            # Get event name in EB API
            context['id'] = self.kwargs['event_id']
            context['discounts'] = Discount.objects.filter(
                event=context['event']
            )
            context['event_name'] = get_event_eb_api(
                get_auth_token(self.request.user),
                context['event'].get().event_id,
            )['name']['text']
            # Get Discounts of the Event

        return context


@method_decorator(login_required, name='dispatch')
class ManageDiscount(FormView, LoginRequiredMixin):

    form_class = DiscountForm
    template_name = 'organizer/create_discount.html'

    def _get_event(self):
        return get_object_or_404(
            Event,
            id=self.kwargs['event_id'],
        )

    def get_form_kwargs(self):
        kwargs = super(ManageDiscount, self).get_form_kwargs()
        if 'discount_id' in self.kwargs:
            discount = Discount.objects.get(
                id=self.kwargs['discount_id'],
            )
            if discount:
                kwargs['initial']['discount_name'] = discount.name
                kwargs['initial']['discount_type']= discount.value_type
                kwargs['initial']['discount_value'] = discount.value
        return kwargs

    def post(self, request, *args, **kwargs):
        form = DiscountForm(
            request.POST
        )

        if not ('discount_id' in self.kwargs):
            self._verify_event_discount(form)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.add_discount(form, self._get_event())
        return HttpResponseRedirect(
            reverse(
                'events_discount',
                kwargs={'event_id': self._get_event().id},
            )
        )

    def add_discount(self, form, event):
        if not ('discount_id' in self.kwargs):
            Discount.objects.create(
                name=form['discount_name'].value(),
                event=event,
                value=form['discount_value'].value(),
                value_type=form['discount_type'].value(),
            )
        else:
            discount = Discount.objects.filter(pk=self.kwargs['discount_id']).update(
                name=form['discount_name'].value(),
                event=event,
                value=form['discount_value'].value(),
                value_type=form['discount_type'].value(),
            )

    def _verify_event_discount(self, form):
        discount = Discount.objects.filter(
            event=self._get_event().id
        )
        if len(discount) > 0:
            error = form.errors.setdefault('__all__', ErrorList())
            error.append(u'You already have a discount for this event')

    def get_context_data(self, **kwargs):
        context = super(ManageDiscount, self).get_context_data(**kwargs)
        context['event'] = self._get_event()
        if 'discount_id' in self.kwargs:
            context['discount'] = get_object_or_404(
                Discount,
                id=self.kwargs['discount_id'],
            )
        return context


@method_decorator(login_required, name='dispatch')
class Error401(TemplateView, LoginRequiredMixin):
    template_name = 'shared/401.html'
