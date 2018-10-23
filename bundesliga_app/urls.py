from django.conf.urls import url
from .views import (
    HomeView,
    CreateLandingpageView,
    ManageDiscount,
    SelectEvents,
    EventDiscountsView,
    DeleteDiscountView,
    LandingPageOrganizerView,
    LandingPageBuyerView,
    ListingPageEventView,
    GetDiscountView,
)

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='index'),
    url(r'^organizer/landing_page/new/$', CreateLandingpageView.as_view(), name='create_landing_page'),
    url(r'^organizer/landing_page/(?P<landing_page_id>[0-9]+)/$', LandingPageOrganizerView.as_view(), name='landing_page_organizer'),
    url(r'^select_events/$', SelectEvents.as_view(), name='select_events'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/$', EventDiscountsView.as_view(), name='events_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/new/$', ManageDiscount.as_view(), name='create_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/(?P<discount_id>[0-9]+)/delete/$', DeleteDiscountView.as_view(), name='delete_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/(?P<discount_id>[0-9]+)/$', ManageDiscount.as_view(), name='modify_discount'),
    url(r'^landing_page/(?P<organizer_id>[0-9]+)/$', LandingPageBuyerView.as_view(), name='landing_page_buyer'),
    url(r'^landing_page/(?P<organizer_id>[0-9]+)/event/(?P<event_id>[0-9]+)/$', ListingPageEventView.as_view(), name='listing_page_event'),
    url(r'^landing_page/(?P<organizer_id>[0-9]+)/event/(?P<event_id>[0-9]+)/get_discount/$', GetDiscountView.as_view(), name='get_discount'),
]
