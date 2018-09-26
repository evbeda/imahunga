from django.conf.urls import url
from .views import (
    CreateDiscount,
    HomeView,
    SelectEvents,
    EventDiscountsView,
)

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='index'),
    url(r'^select_events/$', SelectEvents.as_view(), name='select_events'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/$', EventDiscountsView.as_view(), name='events_discount'),
    url(r'^create_discount/(?P<event_id>[0-9]+)/$', CreateDiscount.as_view(), name='create_discount'),
]
