from django.conf.urls import url
from .views import (
    ManageDiscount,
    HomeView,
    SelectEvents,
    EventDiscountsView,
    DeleteDiscountView,
    LandingPageBuyerView,
    ListingPageEventView,
)

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='index'),
    url(r'^select_events/$', SelectEvents.as_view(), name='select_events'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/$', EventDiscountsView.as_view(), name='events_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/new/$', ManageDiscount.as_view(), name='create_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/(?P<discount_id>[0-9]+)/delete/$', DeleteDiscountView.as_view(), name='delete_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/(?P<discount_id>[0-9]+)/$', ManageDiscount.as_view(), name='modify_discount'),
    url(r'^landing_page/(?P<organizer_id>[0-9]+)/$', LandingPageBuyerView.as_view(), name='landing_page_buyer'),
    url(r'^landing_page/(?P<organizer_id>[0-9]+)/event/(?P<event_id>[0-9]+)/$', ListingPageEventView.as_view(), name='listing_page_event'),
]
