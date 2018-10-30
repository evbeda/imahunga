import os

def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the %s environment variable" % var_name
        raise ImproperlyConfigured(error_msg)

f = open("Dockerfile", "a")
f.write("\nENV API_KEY_DEUTSCHER_SPORTAUSWEIS " + get_env_variable('API_KEY_DEUTSCHER_SPORTAUSWEIS'))
f.write("\nENV SOCIAL_AUTH_EVENTBRITE_KEY " + get_env_variable('SOCIAL_AUTH_EVENTBRITE_KEY'))
f.write("\nENV SOCIAL_AUTH_EVENTBRITE_SECRET " + get_env_variable('SOCIAL_AUTH_EVENTBRITE_SECRET'))
