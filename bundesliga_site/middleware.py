from django.shortcuts import render
from social_django.middleware import SocialAuthExceptionMiddleware
from social_core.exceptions import AuthCanceled


class SocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    def process_exception(self, request, exception):
        if isinstance(exception, AuthCanceled):
            return render(
                request,
                "registration/authcanceled.html",
                {},
            )
        else:
            pass
