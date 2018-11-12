""" This are the methods that supports the behaviour of the views """
from social_django.models import UserSocialAuth
from eventbrite import Eventbrite
from .models import (
    Event,
    Discount,
    EventTicketType,
)
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from bundesliga_site.settings import (
    API_KEY_DEUTSCHER_SPORTAUSWEIS,
    DS_API_URL,
)
from requests import request
from json import loads
from django.core.cache import cache
from django.conf import settings
CACHE_TTL = getattr(settings, "CACHE_TTL")
CACHE_TTL_TICKETS = getattr(settings, "CACHE_TTL_TICKETS")

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
            raise PermissionDenied(_("You don't have access to this event"))
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
        if discount.discount_type.name == 'Event':
            if discount.eventdiscount.event.organizer != self.request.user:
                raise PermissionDenied(_(
                    "You don't have access to this discount")
                )
            if str(discount.eventdiscount.event.id) != self.kwargs['event_id']:
                raise PermissionDenied(_(
                    "This discount does not match with the event")
                )
        elif discount.discount_type.name == 'Ticket Type':
            if discount.tickettypediscount.ticket_type.event.organizer != self.request.user:
                raise PermissionDenied(_(
                    "You don't have access to this discount"))
            if str(discount.tickettypediscount.ticket_type.event.id) != self.kwargs['event_id']:
                raise PermissionDenied(_(
                    "This discount does not match with the event")
                )
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
        return _('UserSocialAuth does not exists!')
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
    events = cache.get('events-' + token)
    if not events:
        eventbrite = Eventbrite(token)
        events = [
            event
            # Status : live, draft, canceled, started, ended, all
            for event in eventbrite.get(
                '/users/me/owned_events/?status=live'
            )['events']
        ]
        cache.set('events-' + token, events, timeout=CACHE_TTL)
    return events


def get_event_eb_api(token, event_id):
    """
    This method will receive an event id and token from logged user
    and returns an event
    """
    event = cache.get('event-' + event_id)
    if not event:
        eventbrite = Eventbrite(token)
        event = eventbrite.get('/events/{}/'.format(event_id))
        cache.set('event-' + event_id, event, timeout=CACHE_TTL)
    return event


def get_venue_eb_api(token, venue_id):
    """
    This method will receive a venue id and token from logged user
    and returns an venue
    """
    venue = cache.get('venue-' + venue_id)
    if not venue:
        eventbrite = Eventbrite(token)
        venue = eventbrite.get('/venues/{}/'.format(venue_id))
        cache.set('venue-' + venue_id, venue, timeout=CACHE_TTL)
    return venue


def get_event_tickets_eb_api(token, event_id):
    """
    This method will receive a event id and token from logged user
    and returns a list of tickets
    """
    tickets = cache.get('tickets-' + event_id)
    if not tickets:
        eventbrite = Eventbrite(token)
        tickets = [
            ticket
            for ticket in eventbrite.get(
                '/events/{}/ticket_classes/'.format(event_id)
            )['ticket_classes']
        ]
        cache.set('tickets-' + event_id, tickets, timeout=CACHE_TTL_TICKETS)
    return tickets


def check_discount_code_in_eb(user, event_id, discount_code):
    eventbrite = Eventbrite(get_auth_token(user))
    organization_id = get_user_eb_api(get_auth_token(user))['id']
    return eventbrite.get(
        '/organizations/{}/discounts/?scope={}&event_id={}&code={}'.format(
            organization_id,
            'event',
            event_id,
            discount_code,
        )
    )


def post_ticket_discount_code_to_eb(user, event_id, discount_code, discount_value, ticket_type, uses):
    eventbrite = Eventbrite(get_auth_token(user))
    organization_id = get_user_eb_api(get_auth_token(user))['id']
    data = {
        "discount": {
            "code": discount_code,
            "event_id": event_id,
            "type": "coded",
            "percent_off": discount_value,
            "ticket_class_ids": ticket_type,
            "quantity_available": uses
        }
    }
    return eventbrite.post(
        '/organizations/{}/discounts/'.format(organization_id),
        data
    )

def post_event_discount_code_to_eb(user, event_id, discount_code, discount_value, uses):
    eventbrite = Eventbrite(get_auth_token(user))
    organization_id = get_user_eb_api(get_auth_token(user))['id']
    data = {
        "discount": {
            "code": discount_code,
            "event_id": event_id,
            "type": "coded",
            "percent_off": discount_value,
            "quantity_available": uses
        }
    }
    return eventbrite.post(
        '/organizations/{}/discounts/'.format(organization_id),
        data
    )


def update_discount_code_to_eb(user, discount_id, uses):
    eventbrite = Eventbrite(get_auth_token(user))
    data = {
        "discount": {
            "quantity_available": uses
        }
    }
    return eventbrite.post(
        '/discounts/{}/'.format(
            discount_id
        ),
        data
    )


def delete_discount_code_from_eb(user, discount_id):

    eventbrite = Eventbrite(get_auth_token(user))
    return eventbrite.delete(
        '/discounts/{}/'.format(
            discount_id
        )
    )


def validate_member_number_ds(member_number):
    """
    This method will receive a possible member number of Deutscher Sportausweis
    and return a json with the info
    """
    url = DS_API_URL
    # "https://admin.sportausweis.de/DSARestWs/RestController.php"

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
        return _('Invalid Request')


def get_ticket_type(user, event_id, ticket_type_id):
    """
    This method will receive an user, event_id from EB
    and ticket_type_id from our BD
    and returns the ticket type in a dict, the key is the id of ticket type in our DB
    and the value is the ticket_type from EB
    """
    event_ticket_type_own = EventTicketType.objects.get(
        id=ticket_type_id
    )
    # Get ticket type of event from EB
    tickets_type_eb = get_event_tickets_eb_api(
        get_auth_token(user),
        event_id
    )
    """ For each event ticket type, get the same ticket from the context
        """
    ticket_type = {}
    for ticket_type_eb in tickets_type_eb:
            # If is the ticket type, save it in a dict a return it
        if ticket_type_eb['id'] == event_ticket_type_own.ticket_id_eb:
            ticket_type[str(ticket_type_id)] = ticket_type_eb
            return ticket_type
