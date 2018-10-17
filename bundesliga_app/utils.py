""" This are the methods that supports the behaviour of the views """
from social_django.models import UserSocialAuth
from eventbrite import Eventbrite
from .models import (
    Event,
    Discount,
)
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from bundesliga_site.settings import API_KEY_DEUTSCHER_SPORTAUSWEIS
from requests import request
from json import loads


class EventAccessMixin(object):
    """
    This mixin deny the access to the event
    if the logged user is not the owner of the event
    """
    def get_event(self):
        event = get_object_or_404(
            Event,
            id=self.kwargs['event_id'],
            is_active=True,
        )
        if event.organizer != self.request.user:
            raise PermissionDenied("You don't have access to this event")
        return event


class DiscountAccessMixin(EventAccessMixin):
    """
    This mixin deny the access to a discount
    if the logged user is not the owner of the discount
    also the access to the event is prohibited
    """
    def get_discount(self):
        discount = get_object_or_404(
            Discount,
            id=self.kwargs['discount_id'],
        )
        if discount.event.organizer != self.request.user:
            raise PermissionDenied("You don't have access to this discount")
        return discount


def get_auth_token(user):

    """
    This method will receive a user and
    returns its repesctive social_auth token
    """
    try:
        token = user.social_auth.get(
            provider='eventbrite'
        ).access_token
    except UserSocialAuth.DoesNotExist:
        return 'UserSocialAuth does not exists!'
    return token


def get_user_eb_api(token):
    """
    This method will receive a valid token for user of EB,
    and returns the user of EB
    """
    eventbrite = Eventbrite(token)
    return eventbrite.get('/users/me/')


def get_events_user_eb_api(token):
    """
    This method will receive a valid token for user of EB,
    and returns a list of events with specific state
    """
    eventbrite = Eventbrite(token)
    return [
        event
        # Status : live, draft, canceled, started, ended, all
        for event in eventbrite.get(
            '/users/me/owned_events/?status=live'
        )['events']
    ]


def get_event_eb_api(token, event_id):
    """
    This method will receive an event id and token from logged user
    and returns an event
    """

    eventbrite = Eventbrite(token)
    return eventbrite.get('/events/{}/'.format(event_id))


def get_venue_eb_api(token, venue_id):
    """
    This method will receive a venue id and token from logged user
    and returns an venue
    """

    eventbrite = Eventbrite(token)
    return eventbrite.get('/venues/{}/'.format(venue_id))


def get_event_tickets_eb_api(token, event_id):
    """
    This method will receive a event id and token from logged user
    and returns a list of tickets
    """

    eventbrite = Eventbrite(token)
    return [
        ticket
        for ticket in eventbrite.get(
            '/events/{}/ticket_classes/'.format(event_id)
        )['ticket_classes']
    ]


def post_discount_code_to_eb(token, event_id, discount_code, discount_value):
    eventbrite = Eventbrite(token)
    organization_id = get_user_eb_api(token)['id']
    data = {
        "discount": {
            "code": discount_code,
            "event_id": event_id,
            "type": "coded",
            "percent_off": discount_value,
            "quantity_available": 1
        }
    }
    return eventbrite.post(
        '/organizations/{}/discounts/'.format(organization_id),
        data
    )


def validate_member_number_ds(member_number):
    """
    This method will receive a possible member number of Deutscher Sportausweis
    and return a json with the info
    """
    url = "https://admin.sportausweis.de/DSARestWs/RestController.php"

    querystring = {
        "request": "validateCard",
        "CardId": member_number,
    }

    headers = {
        'APIKEY': API_KEY_DEUTSCHER_SPORTAUSWEIS,
        'Accept': "application/json",
    }

    response = request(
        "GET",
        url,
        headers=headers,
        params=querystring
    )
    if response.status_code == 200:
        # Return the text of response as JSON
        return loads(response.text)
    else:
        return 'Invalid Request'
