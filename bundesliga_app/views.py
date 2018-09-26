from bundesliga_app.models import Event
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from eventbrite import Eventbrite
from .models import Discount
from .utils import get_auth_token


@method_decorator(login_required, name='dispatch')
class HomeView(TemplateView, LoginRequiredMixin):

    """ This is the index view.
    Here we show all the events of the user in our app """

    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['events'] = Event.objects.filter(organizer=self.request.user)
        return context


@method_decorator(login_required, name='dispatch')
class SelectEvents(TemplateView, LoginRequiredMixin):

    """ This is the index view. Here we display all the banners that the user
    has created """

    template_name = 'organizer/select_events.html'

    def _get_event(self):
        eventbrite = Eventbrite(
            get_auth_token(self.request.user),
        )
        return [
            event
            # Status : live, draft, canceled, started, ended, all
            for event in eventbrite.get(
                '/users/me/owned_events/?status=live,draft'
            )['events']
        ]

    def post(self, *args, **kwargs):
        events = self._get_event()
        request_body_elements = str(self.request.body).split('event_')
        request_body_elements.pop(0)
        events_id = []
        # Put in array all the events id selected
        for event_id in request_body_elements:
            event = event_id.split('=')
            events_id.append(event[0])

        # For each event in the api, verify if the selected ones are corrects
        for event_in_api in events:
            # If the event id is an event of organizer
            if event_in_api['id'] in events_id:
                # Verify if this event already exist
                if not Event.objects.filter(event_id=event_in_api['id']).exists():
                    Event.objects.create(
                        event_id=event_in_api['id'],
                        name=event_in_api['name']['text'],
                        organizer=self.request.user,
                    )
        return HttpResponseRedirect(reverse('index'))

    def get_context_data(self, **kwargs):
        # import ipdb; ipdb.set_trace()
        context = super(SelectEvents, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        eventbrite = Eventbrite(
            get_auth_token(self.request.user),
        )
        context['me'] = eventbrite.get('/users/me/')
        # Bring live and draf events of user
        context['events'] = self._get_event()
        return context


@method_decorator(login_required, name='dispatch')
class EventDiscountsView(TemplateView, LoginRequiredMixin):

    """ This is the the Event Discounts view,
    here the organizer can manage the discounts of the event"""

    template_name = 'organizer/event_discounts.html'

    def get_context_data(self, **kwargs):
        context = super(EventDiscountsView, self).get_context_data(**kwargs)
        context['event'] = get_object_or_404(
            Event,
            event_id=self.kwargs['event_id'],
        )
        # Get Discounts of the Event
        context['discounts'] = Discount.objects.filter(
            event=self.kwargs['event_id']
        )
        return context


@method_decorator(login_required, name='dispatch')
class CreateDiscount(TemplateView, LoginRequiredMixin):
    template_name = 'organizer/create_discount.html'

    def _get_event(self):
        return get_object_or_404(
            Event,
            event_id=self.kwargs['event_id'],
        )

    def post(self, *args, **kwargs):
        discount_value = float(self.request.POST['discount'])
        discount_type = self.request.POST['discount_type']
        Discount.objects.create(
            name=self.request.POST['discount_name'],
            event=self._get_event(),
            value=discount_value,
            value_type=discount_type,
        )
        return HttpResponseRedirect(
            reverse(
                'events_discount',
                kwargs={'event_id': self._get_event().event_id},
            )
        )

    def get_context_data(self, **kwargs):
        context = super(CreateDiscount, self).get_context_data(**kwargs)
        context['event'] = self._get_event()
        return context
