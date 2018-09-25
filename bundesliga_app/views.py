from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
from eventbrite import Eventbrite
from bundesliga_app.models import Event
from django.http import HttpResponseRedirect
from .utils import get_auth_token
from .models import MemberType, Discount


@method_decorator(login_required, name='dispatch')
class HomeView(ListView, LoginRequiredMixin):

    """ This is the index view. Here we display all the banners that the user
    has created """

    template_name = 'index.html'

    queryset = Event.objects.all()


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
        # import ipdb; ipdb.set_trace()
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
            else:
                continue
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
class CreateDiscount(TemplateView, LoginRequiredMixin):
    template_name = 'organizer/createDiscount.html'

    def post(self, *args, **kwargs):
        # import ipdb
        # ipdb.set_trace()
        selectedItems = self.request.POST.getlist('select_membertype')
        for i in range(0, len(selectedItems)):
            index = selectedItems[i][-1]
            discount_value = float(self.request.POST['discount_' + index])
            discount_type = self.request.POST['discount_type_' + index]
            membertype = MemberType.objects.get(id=index)
            discount = Discount(discount_name=self.request.POST['discount_name_' + index],
                                event_id=1,
                                membertype=membertype,
                                discount_value=discount_value,
                                discount_value_type=discount_type,
                                )
            discount.save()
        return redirect("index")

    def get_context_data(self, **kwargs):
        context = super(CreateDiscount, self).get_context_data(**kwargs)
        context['membertypelist'] = MemberType.objects.all()
        return context
