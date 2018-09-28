""" This are the methods that supports the behaviour of the views """
from social_django.models import UserSocialAuth


def get_auth_token(user):

    """
    This method will receive a user and
    return its repesctive social_auth token
    """
    try:
        token = user.social_auth.get(
            provider='eventbrite'
        ).access_token
    except UserSocialAuth.DoesNotExist:
        return 'UserSocialAuth does not exists!'
    return token
