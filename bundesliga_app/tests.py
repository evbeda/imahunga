from django.test import TestCase
from unittest import skip
from .factories import (
    AuthFactory,
    DiscountFactory,
    EventFactory,
    OrganizerFactory,
)
from .views import (
    CreateDiscount,
    SelectEvents,
)
from mock import patch
from django.apps import apps
from bundesliga_app.apps import BundesligaAppConfig
from bundesliga_app.utils import get_auth_token


# Create your tests here.
MOCK_EVENTS_API = {
    'name': {
        'text': 'EventoCualquiera',
        'html': 'EventoCualquiera'
    },
    'description': {
        'text': None,
        'html': None
    },
    'id': '50607739110',
    'url': 'https://www.eventbrite.com.ar/e/eventocualquiera-tickets-50607739110',
    'start': {
          'timezone': 'America/Caracas',
          'local': '2018-11-03T19:00:00',
        'utc': '2018-11-03T23:00:00Z'
    },
    'end': {
        'timezone': 'America/Caracas',
        'local': '2018-11-03T22:00:00',
        'utc': '2018-11-04T02:00:00Z'
    },
    'organization_id': '226660633266',
    'created': '2018-09-24T17:32:37Z',
    'changed': '2018-09-26T17:07:55Z',
    'capacity': 10,
    'capacity_is_custom': False,
    'status': 'live',
    'currency': 'ARS',
    'listed': False,
    'shareable': True,
    'invite_only': False,
    'online_event': False,
    'show_remaining': False,
    'tx_time_limit': 480,
    'hide_start_date': False,
    'hide_end_date': False,
    'locale': 'es_AR',
    'is_locked': False,
    'privacy_setting': 'unlocked',
    'is_series': False,
    'is_series_parent': False,
    'is_reserved_seating': False,
    'show_pick_a_seat': False,
    'show_seatmap_thumbnail': False,
    'show_colors_in_seatmap_thumbnail': False,
    'source': 'create_2.0',
    'is_free': True,
    'version': '3.0.0',
    'logo_id': '50285339',
    'organizer_id': '17688321548',
    'venue_id': None,
    'category_id': None,
    'subcategory_id': None,
    'format_id': None,
    'resource_uri': 'https://www.eventbriteapi.com/v3/events/50607739110/',
    'is_externally_ticketed': False,
    'logo': {
        'crop_mask': {
              'top_left': {
                'x': 0,
                'y': 43
              },
            'width': 524,
            'height': 262
        },
        'original': {
            'url': 'https://img.evbuc.com/https%3A%2F%2Fcdn.evbuc.com%2Fimages%2F50285339%2F226660633266%2F1%2Foriginal.jpg?auto=compress&s=76bcc2208a37ed4a6cf52ec9d204fe1c',
            'width': 525,
            'height': 350
        },
        'id': '50285339',
        'url': 'https://img.evbuc.com/https%3A%2F%2Fcdn.evbuc.com%2Fimages%2F50285339%2F226660633266%2F1%2Foriginal.jpg?h=200&w=450&auto=compress&rect=0%2C43%2C524%2C262&s=393615fb1d44a82eb37a2cb2fafa9ac7',
        'aspect_ratio': '2',
        'edge_color': '#6b7384',
        'edge_color_set': True
    }
}


class BundesligaAppConfigTest(TestCase):
    def test_apps(self):
        self.assertEqual(BundesligaAppConfig.name, 'bundesliga_app')
        self.assertEqual(apps.get_app_config('bundesliga_app').name, 'bundesliga_app')


class TestBase(TestCase):
    def setUp(self):
        self.organizer = OrganizerFactory()
        self.auth = AuthFactory(
            provider='eventbrite',
            user=self.organizer,
        )
        login = self.client.login(
            username=self.auth.user.username,
            password='12345',
        )
        return login

class AuthTokenTest(TestBase):
    def setUp(self):
        super(AuthTokenTest, self).setUp()

    def test_get_auth_token(self):
        self.assertEqual(
            get_auth_token(self.organizer),
            self.organizer.social_auth.get(provider='eventbrite').access_token
        )

    def test_get_auth_token_invalid_user(self):
        no_log_organizer = OrganizerFactory()
        self.assertEqual(
            get_auth_token(no_log_organizer),
            'UserSocialAuth does not exists!'
        )


class HomeViewTest(TestBase):
    def setUp(self):
        super(HomeViewTest, self).setUp()
        # Create 4 Active Events of logged organizer
        self.events = EventFactory.create_batch(
            4,
            organizer=self.organizer,
            is_active=True,
        )
        # Create inactive event of logged organizer
        self.no_active_events = EventFactory(
            organizer=self.organizer,
            is_active=False,
        )
        # Create inactive event of another organizer
        self.events_another_organizer = EventFactory.create_batch(
            4,
            organizer=OrganizerFactory(),  # Random organizer
            is_active=True,
        )
        self.response = self.client.get('/')

    def test_homepage(self):
        self.assertEqual(self.response.status_code, 200)

    def test_home_url_has_index_template(self):
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'index.html',
        )

    def test_events_organizer(self):
        for event in self.events:
            self.assertContains(
                self.response,
                event,
            )

    def test_events_organizer_not_active(self):
        self.assertNotContains(
            self.response,
            self.no_active_events,
        )

    def test_events_another_organizer(self):
        for event in self.events_another_organizer:
            self.assertNotContains(
                self.response,
                event,
            )


class EventDiscountsViewTest(TestBase):
    def setUp(self):
        super(EventDiscountsViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        self.events_discount = DiscountFactory(
            event=self.event,
        )
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.event_id)
        )

    def test_event_discounts(self):
        self.assertEqual(self.response.status_code, 200)

    def test_event_discounts_url_has_correct_template(self):
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/event_discounts.html',
        )

    def test_event_in_response(self):
        self.assertContains(self.response, self.event)

    def test_events_discounts_in_response(self):
        self.assertContains(
            self.response,
            self.events_discount,
        )
        # The event of the discount is the same of the event in response
        self.assertEqual(
            self.response.context_data['event'].name,
            self.events_discount.event.name
        )


class CreateDiscountViewTest(TestBase):
    def setUp(self):
        super(CreateDiscountViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )

        self.response = self.client.get(
            '/create_discount/{}/'.format(self.event.event_id)
        )

    def test_create_event_discount(self):
        self.assertEqual(self.response.status_code, 200)

    def test_create_event_discount_url_has_correct_template(self):
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/create_discount.html',
        )

    def test_event_in_response(self):
        self.assertEqual(
            int(self.response.context_data['event'].event_id),
            self.event.event_id,
        )



# @patch('bundesliga_app.utils.get_auth_token', return_value=123456)
# @patch('bundesliga_app.views.SelectEvents._get_event', return_value=MOCK_EVENTS_API)
class SelectEventsViewTest(TestBase):
    def setUp(self):
        super(SelectEventsViewTest, self).setUp()
        # Mock user access token
        self.get_auth_token_patcher = patch(
            'bundesliga_app.utils.get_auth_token',
            return_value=123456,
        )
        self.mock_get_auth_token = self.get_auth_token_patcher.start()

        self.get_events_api_patcher = patch(
            'bundesliga_app.views.SelectEvents._get_event',
            return_value=123456,
        )
        self.mock_get_events_api = self.get_events_api_patcher.start()
        self.response = self.client.get('/select_events/')

    @skip("Mock for API does not works yet")
    def test_select_events(self):
        self.assertEqual(self.response.status_code, 200)

    @skip("Mock for API does not works yet")
    def test_select_events_url_has_the_correct_template(self):
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/select_events.html',
        )

    @skip("Mock for API does not works yet")
    def test_organizer_in_context(self):
        self.assertContains(
            self.response,
            self.organizer,
        )

    @skip("Mock for API does not works yet")
    def test_date_conversor(self):
        self.response.context_data['events'] = MOCK_EVENTS_API
        self.assertEqual(
             self.response.context_data['view'].get_local_date(MOCK_EVENTS_API),
            'November 03, 2018'
        )
