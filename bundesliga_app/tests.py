from django.test import (
    TestCase,
    RequestFactory,
)
from unittest import skip
from .factories import (
    AuthFactory,
    DiscountFactory,
    EventFactory,
    OrganizerFactory,
)
from .views import (
    ManageDiscount,
    SelectEvents,
)
from django.urls import reverse, reverse_lazy
from django.views.generic.base import TemplateView
from mock import patch
from django.apps import apps
from urllib.parse import urlencode
from bundesliga_app.apps import BundesligaAppConfig
from bundesliga_app.utils import (
    get_auth_token,
    EventAccessMixin,
    DiscountAccessMixin,
    get_local_date
)
from .models import (
    Discount,
    Event,
)
from bundesliga_app.mocks import (
    MOCK_EVENT_API,
    MOCK_USER_API,
    MOCK_LIST_EVENTS_API,
    get_mock_events_api,
)
from django.http import Http404
from django.core.exceptions import PermissionDenied

# Create your tests here.


class BundesligaAppConfigTest(TestCase):
    def test_apps(self):
        self.assertEqual(BundesligaAppConfig.name, 'bundesliga_app')
        self.assertEqual(
            apps.get_app_config('bundesliga_app').name,
            'bundesliga_app',
        )


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


@patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
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
        # Create active event of another organizer
        self.events_another_organizer = EventFactory.create_batch(
            4,
            organizer=OrganizerFactory(),  # Random organizer
            is_active=True,
        )

    def test_homepage(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        self.assertEqual(self.response.status_code, 200)

    def test_home_url_has_index_template(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'index.html',
        )

    def test_events_organizer(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        for event in self.events:
            self.assertIn(
                event.id,
                self.response.context_data['events']
            )

    def test_events_organizer_not_active(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        self.assertNotContains(
            self.response,
            self.no_active_events,
        )

    def test_events_another_organizer(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        for event in self.events_another_organizer:
            self.assertNotContains(
                self.response,
                event,
            )

    def test_get_discount_if_exists(self, mock_get_event_eb_api):
        discount = DiscountFactory(
            event=self.events[0],
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get('/')
        self.assertEqual(
            self.response.context['events'][self.events[0].id]['discount'],
            discount.value,
        )


@patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
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

    def test_event_discounts(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertEqual(self.response.status_code, 200)

    def test_event_discounts_url_has_correct_template(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/event_discounts.html',
        )

    def test_event_in_response(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertContains(
            self.response,
            self.event.id,
        )
        self.assertEqual(
            self.response.context_data['event'],
            self.event,
        )

    def test_events_discounts_in_response(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertContains(
            self.response,
            self.events_discount,
        )
        # The event of the discount is the same of the event in response
        self.assertEqual(
            int(self.response.context_data['id']),
            self.events_discount.event.id,
        )


class CreateDiscountViewTest(TestBase):
    def setUp(self):
        super(CreateDiscountViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )

        self.response = self.client.get(
            '/events_discount/{}/new/'.format(self.event.id)
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
            self.response.context_data['event'].id,
            self.event.id,
        )

    def test_create_discount_wrong_percentage_value_negative(self):
        self.response = self.client.post(
            '/events_discount/{}/new/'.format(self.event.id),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': -50,
            },
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(
            self.response,
            'Ensure this value is greater than or equal to 0.'
        )
        self.assertEqual(
            len(Discount.objects.filter(event=self.event)),
            0,
        )

    def test_create_discount_wrong_percentage_value_too_high(self):
        self.response = self.client.post(
            '/events_discount/{}/new/'.format(self.event.id),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 200,
            },
        )
        self.assertContains(
            self.response,
            'Ensure this value is less than or equal to 100.'
        )
        self.assertEqual(
            len(Discount.objects.filter(event=self.event)),
            0,
        )

    def test_create_second_discount(self):
        self.discount = DiscountFactory(
            event=self.event,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.post(
            '/events_discount/{}/new/'.format(self.event.id),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
            },
        )
        self.assertContains(
            self.response,
            'You already have a discount for this event')


class ModifyDiscountViewTest(TestBase):
    def setUp(self):
        super(ModifyDiscountViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )

        self.discount = DiscountFactory(
            event=self.event,
            value=100.0,
            value_type="percentage",
        )

        self.response = self.client.get(
            '/events_discount/{}/{}/'.format(
                self.event.id,
                self.discount.id,
            )
        )

    def test_modify_event_discount(self):
        self.assertEqual(self.response.status_code, 200)

    def test_modify_event_discount_url_has_correct_template(self):
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/create_discount.html',
        )

    def test_event_in_response(self):
        self.assertEqual(
            self.response.context_data['event'].id,
            self.event.id,
        )

    def test_discount_in_response(self):
        self.assertEqual(
            self.response.context_data['discount'].id,
            self.discount.id,
        )

    def test_modify_discount_correct_percentage_value(self):
        self.response = self.client.post(
            '/events_discount/{}/{}/'.format(
                self.event.id,
                self.discount.id,
            ),
            {
                'discount_name': self.discount.name,
                'discount_type': 'percentage',
                'discount_value': 20,
            },
        )
        updated_discount = Discount.objects.get(id=self.discount.id)
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(updated_discount.value_type, 'percentage')
        self.assertEqual(updated_discount.value, 20)
        self.assertEqual(
            len(Discount.objects.filter(event=self.event)),
            1,
        )

    def test_modify_discount_low_percentage_value(self):

        self.response = self.client.post(
            '/events_discount/{}/{}/'.format(
                self.event.id,
                self.discount.id,
            ),
            {
                'discount_name': self.discount.name,
                'discount_type': 'percentage',
                'discount_value': -10,
            },
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(
            self.response,
            'Ensure this value is greater than or equal to 0.'
        )
        self.assertEqual(
            len(Discount.objects.filter(event=self.event)),
            1,
        )

    def test_modify_discount_too_high_percentage_value(self):

        self.response = self.client.post(
            '/events_discount/{}/{}/'.format(
                self.event.id,
                self.discount.id,
            ),
            {
                'discount_name': self.discount.name,
                'discount_type': 'percentage',
                'discount_value': 150,
            },
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(
            self.response,
            'Ensure this value is less than or equal to 100.'
        )
        self.assertEqual(
            len(Discount.objects.filter(event=self.event)),
            1,
        )


class DeleteDiscountViewTest(TestBase):
    def setUp(self):
        super(DeleteDiscountViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )

        self.discount = DiscountFactory(
            event=self.event,
            value=100.0,
            value_type="percentage",
        )

        self.response = self.client.get(
            '/events_discount/{}/{}/delete/'.format(
                self.event.id,
                self.discount.id,
            )
        )

    def test_delete_event_discount(self):
        self.assertEqual(self.response.status_code, 200)

    def test_delete_event_discount_url_has_correct_template(self):
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/delete_discount.html',
        )

    def test_event_in_response(self):
        self.assertEqual(
            self.response.context_data['event'].id,
            self.event.id,
        )

    def test_discount_in_response(self):
        self.assertEqual(
            self.response.context_data['discount'].id,
            self.discount.id,
        )

    def test_press_delete_discount(self):
        self.response = self.client.get(
            '/events_discount/{}/{}/delete/'.format(
                self.event.id,
                self.discount.id,
            ),
            follow=True,
        )

        self.assertContains(
            self.response, 'Are you sure you want to delete the discount')

    def test_confirm_delete_discount(self):
        self.response = self.client.post(
            '/events_discount/{}/{}/delete/'.format(
                self.event.id,
                self.discount.id,
            ),
        )

        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(
            len(Discount.objects.filter(event=self.event)),
            0,
        )


@patch('bundesliga_app.views.get_user_eb_api', return_value=MOCK_USER_API)
@patch('bundesliga_app.views.get_events_user_eb_api',
       return_value=MOCK_LIST_EVENTS_API,
       )
class SelectEventsViewTest(TestBase):
    def setUp(self):
        super(SelectEventsViewTest, self).setUp()

    def test_select_events(self,
                           mock_get_events_user_eb_api,
                           mock_get_user_eb_api,
                           ):
        self.response = self.client.get('/select_events/')
        self.assertEqual(self.response.status_code, 200)

    def test_select_events_correct_template(self,
                                            mock_get_events_user_eb_api,
                                            mock_get_user_eb_api,
                                            ):
        self.response = self.client.get('/select_events/')
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/select_events.html',
        )

    def test_organizer_in_context(self,
                                  mock_get_events_user_eb_api,
                                  mock_get_user_eb_api,
                                  ):
        self.response = self.client.get('/select_events/')
        self.assertEqual(
            self.response.context_data['user'],
            self.organizer,
        )

    def test_date_conversor(self,
                            mock_get_events_user_eb_api,
                            mock_get_user_eb_api,
                            ):
        self.response = self.client.get('/select_events/')
        for event in self.response.context_data['events']:
            self.assertEqual(
                event['local_date'],
                'November 03, 2018',
            )

    def test_selected_events(self,
                             mock_get_events_user_eb_api,
                             mock_get_user_eb_api,
                             ):
        # One event for the organizer, a "selected" event
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        self.response = self.client.get('/select_events/')
        selected_events = Event.objects.filter(
            organizer=self.organizer
        ).filter(is_active=True)
        for selected_event in selected_events:
            self.assertIn(
                selected_event.event_id,
                self.response.context_data['already_selected_id'],
            )

    def test_post_event_new(self,
                            mock_get_events_user_eb_api,
                            mock_get_user_eb_api,
                            ):
        event_mock_api_eb = mock_get_events_user_eb_api.return_value[0]
        self.response = self.client.post(
            path='/select_events/',
            data=urlencode({
                'event_' + event_mock_api_eb['id']: 'on',
            }),
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(
            len(Event.objects.filter(event_id=event_mock_api_eb['id'])),
            1,
        )

    def test_post_event_update(self,
                               mock_get_events_user_eb_api,
                               mock_get_user_eb_api,
                               ):
        """ One event for the organizer, a "selected" event
        with the same event_id of the mocked event api eb """
        event_mock_api_eb = mock_get_events_user_eb_api.return_value[0]
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
            event_id=event_mock_api_eb['id'],
        )
        self.response = self.client.post(
            path='/select_events/',
            data=urlencode({
                'event_' + event_mock_api_eb['id']: 'on',
            }),
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(
            len(Event.objects.filter(event_id=event_mock_api_eb['id'])),
            1,
        )

    def test_post_event_update_unselect(self,
                                        mock_get_events_user_eb_api,
                                        mock_get_user_eb_api,
                                        ):
        """ One event for the organizer, a "selected" event
        with the same event_id of the mocked event api eb """
        event_mock_api_eb = mock_get_events_user_eb_api.return_value[0]
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
            event_id=event_mock_api_eb['id'],
        )
        self.response = self.client.post(
            path='/select_events/',
        )
        event_in_db = Event.objects.filter(event_id=event_mock_api_eb['id'])
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(
            len(event_in_db),
            1,
        )
        self.assertFalse(
            event_in_db.get().is_active
        )

class EventAccessMixinTest(TestBase):
    class DummyView(TemplateView, EventAccessMixin):
        template_name = 'any_template.html'  # TemplateView requires this attribute
        kwargs = ''
        request = RequestFactory()
        request.user = ''

    def setUp(self):
        super(EventAccessMixinTest, self).setUp()
        self.view = self.DummyView()

    def test_rise_exception_permission_denied(self):
        self.organizer_2 = OrganizerFactory()
        event = EventFactory(
            organizer=self.organizer_2,
            is_active=True,
        )
        # Setup request and view.
        self.view.kwargs = {'event_id': event.id}
        # the logged user is user 0 and the organizer of the event is user 1
        self.view.request.user = self.organizer
        self.view.response = '/events_discount/{}/new/'.format(event.id)

        with self.assertRaises(PermissionDenied) as permission_denied:
                self.view.get_event()
        self.assertEqual(permission_denied.exception.args[0], "You don't have access to this event")

    def test_valid_event_owner(self):
        event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        # Setup request and view.
        self.view.kwargs = {'event_id': event.id}
        # the logged user is user 0 and the organizer of the event is user 1
        self.view.request.user = self.organizer
        self.view.response = '/events_discount/{}/new/'.format(event.id)
        self.assertEqual(self.view.get_event(), event)

    def test_rise_exception_404(self):
        # Setup request and view.
        self.view.kwargs = {'event_id': 4}
        # the logged user is user 0 and the organizer of the event is user 1
        self.view.request.user = self.organizer
        self.view.response = '/events_discount/{}/new/'.format(4)

        with self.assertRaises(Http404):
                self.view.get_event()


class DiscountAccessMixinTest(TestBase):
    class DummyView(TemplateView, DiscountAccessMixin):
        template_name = 'any_template.html'  # TemplateView requires this attribute
        kwargs = ''
        request = RequestFactory()
        request.user = ''

    def setUp(self):
        super(DiscountAccessMixinTest, self).setUp()
        self.view = self.DummyView()

    def test_rise_exception_permission_denied(self):
        event = EventFactory(
            organizer=OrganizerFactory(),
            is_active=True,
        )
        event2 = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        discount = DiscountFactory(
            event=event,
        )
        # Setup request and view.
        self.view.kwargs = {
            'event_id': event2.id,
            'discount_id': discount.id,
        }
        # the logged user is user 0 and the organizer of the event is user 1
        self.view.request.user = self.organizer
        self.view.response = 'events_discount/{}/{}/'.format(event2.id, discount.id)

        with self.assertRaises(PermissionDenied) as permission_denied:
                self.view.get_discount()
        self.assertEqual(permission_denied.exception.args[0], "You don't have access to this discount")

    def test_valid_discount_owner(self):
        event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        discount = DiscountFactory(
            event=event,
        )
        # Setup request and view.
        self.view.kwargs = {
            'event_id': event.id,
            'discount_id': discount.id,
        }
        # the logged user is user 0 and the organizer of the event is user 1
        self.view.request.user = self.organizer
        self.view.response = 'events_discount/{}/{}/'.format(event.id, discount.id)
        self.assertEqual(self.view.get_discount(), discount)

    def test_rise_exception_404(self):
        event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        # Setup request and view.
        self.view.kwargs = {
            'event_id': event.id,
            'discount_id': 8,
        }
        # the logged user is user 0 and the organizer of the event is user 1
        self.view.request.user = self.organizer
        self.view.response = 'events_discount/{}/{}/'.format(event.id, 8)

        with self.assertRaises(Http404):
                self.view.get_discount()
