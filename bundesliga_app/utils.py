""" This are the methods that supports the behaviour of the views """
from social_django.models import UserSocialAuth
from eventbrite import Eventbrite
from .models import (
    Event,
    Discount,
)
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied


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
