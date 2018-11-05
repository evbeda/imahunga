from django.conf.urls import url
from .views import (
    ManageDiscountEvent,
    ManageDiscountTicketType,
    HomeView,
    SelectEvents,
    EventDiscountsView,
    DeleteDiscountView,
    LandingPageBuyerView,
    ListingPageEventView,
    ActivateLanguageView
)

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='index'),
    url(r'^select_events/$', SelectEvents.as_view(), name='select_events'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/$', EventDiscountsView.as_view(), name='events_discount'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/ticket_type/(?P<ticket_type_id>[0-9]+)/new/$', ManageDiscountTicketType.as_view(), name='create_discount_ticket_type'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/ticket_type/(?P<ticket_type_id>[0-9]+)/(?P<discount_id>[0-9]+)/$', ManageDiscountTicketType.as_view(), name='modify_discount_ticket_type'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/event/new/$', ManageDiscountEvent.as_view(), name='create_discount_event'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/event/(?P<discount_id>[0-9]+)/$', ManageDiscountEvent.as_view(), name='modify_discount_event'),
    url(r'^events_discount/(?P<event_id>[0-9]+)/(?P<discount_id>[0-9]+)/delete/$', DeleteDiscountView.as_view(), name='delete_discount'),
    url(r'^landing_page/(?P<organizer_id>[0-9]+)/$', LandingPageBuyerView.as_view(), name='landing_page_buyer'),
    url(r'^landing_page/(?P<organizer_id>[0-9]+)/event/(?P<event_id>[0-9]+)/$', ListingPageEventView.as_view(), name='listing_page_event'),
    url(r'language/activate/(?P<language_code>[a-z]+)/', ActivateLanguageView.as_view(), name='activate_language'),
]
