""" This are the methods that supports the behaviour of the views """
from social_django.models import UserSocialAuth
from eventbrite import Eventbrite


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


def get_events_user_eb_api(token):
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


def get_local_date(event):
    """
    This method will receive an event and
    returns a format date
    """

    for value in event['start'].values():
        date_complete = value
    date_complete = date_complete.split('-')
    day = date_complete[2].split('T')[0]
    months = [
        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December',
    ]
    month = months[int(date_complete[1]) - 1]
    year = date_complete[0]
    return '{} {}, {}'.format(month, day, year)
