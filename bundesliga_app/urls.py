from django.conf.urls import url
from .views import (
    CreateDiscount,
    Error401,
    EventDiscountsView,
    ManageDiscount,
    HomeView,
    SelectEvents,
)

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='index'),
    url(r'^select_events/$', SelectEvents.as_view(), name='select_events'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/$', EventDiscountsView.as_view(), name='events_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/new/$', ManageDiscount.as_view(), name='create_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/(?P<discount_id>[0-9]+)/$', ManageDiscount.as_view(), name='modify_discount'),
    url(r'^create_discount/(?P<event_id>[0-9]+)/$', CreateDiscount.as_view(), name='create_discount'),
    url(r'^invalid_access/$', Error401.as_view(), name='invalid_access'),
]
