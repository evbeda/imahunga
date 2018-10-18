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
from django.views.generic.base import TemplateView
from mock import patch
from django.apps import apps
from urllib.parse import urlencode
from bundesliga_app.apps import BundesligaAppConfig
from bundesliga_app.utils import (
    get_auth_token,
    EventAccessMixin,
    DiscountAccessMixin,
    get_user_eb_api,
    get_events_user_eb_api,
    get_event_eb_api,
    get_venue_eb_api,
    get_event_tickets_eb_api,
    check_discount_code_in_eb,
    post_discount_code_to_eb,
    validate_member_number_ds,
)
from .models import (
    Discount,
    Event,
)
from .forms import GetDiscountForm
from bundesliga_app.mocks import (
    MOCK_DS_API_VALID_NUMBER,
    MOCK_DS_API_INVALID_NUMBER,
    MOCK_DS_API_INVALID_REQUEST,
    MOCK_EVENT_API,
    MOCK_USER_API,
    MOCK_LIST_EVENTS_API,
    MOCK_VENUE_API,
    MOCK_EVENT_TICKETS,
    MOCK_DISCOUNT_DOESNT_EXIST_IN_EB,
    MOCK_POST_DISCOUNT_CODE_TO_EB,
    MOCK_DISCOUNT_EXISTS_IN_EB_NO_USAGE,
    MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE,
    get_mock_events_api,
    get_mock_event_api_without_venue,
    get_mock_event_api_free,
    get_mock_event_tickets_api_free,
    get_mock_event_tickets_api_paid,
    get_mock_event_tickets_api_paid_inverse_position,
)
from django.http import Http404
from django.core.exceptions import PermissionDenied
import datetime


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


@patch('bundesliga_app.utils.Eventbrite.get')
class UtilsApiEBTest(TestCase):

    def test_get_user_eb_api(self, mock_api_call):
        get_user_eb_api('TEST')
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][0][0],
            '/users/me/',
        )

    def test_get_events_user_eb_api(self, mock_api_call):
        get_events_user_eb_api('TEST')
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][0][0],
            '/users/me/owned_events/?status=live',
        )

    def test_get_event_eb_api(self, mock_api_call):
        get_event_eb_api('TEST', '1')
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][0][0],
            '/events/1/',
        )

    def test_get_venue_eb_api(self, mock_api_call):
        get_venue_eb_api('TEST', '1')
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][0][0],
            '/venues/1/',
        )

    def test_get_event_tickets_eb_api(self, mock_api_call):
        get_event_tickets_eb_api('TEST', '1')
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][0][0],
            '/events/1/ticket_classes/',
        )

    @patch('bundesliga_app.utils.get_user_eb_api', return_value=MOCK_USER_API)
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE)
    def test_check_discount_code_in_eb(self,
                                       mock_check_discount_code_in_eb,
                                       mock_get_user_eb_api,
                                       mock_api_get_call
                                       ):

        result = check_discount_code_in_eb('TEST', '1', '1')
        self.assertEquals(
            mock_api_get_call.call_args_list[0][0][0],
            '/organizations/1234/discounts/?scope=event&event_id=1&code=1'
        )

    @patch('bundesliga_app.utils.Eventbrite.post', return_value={'id': '1'})
    @patch('bundesliga_app.views.get_user_eb_api', return_value=MOCK_USER_API)
    def test_post_discount_code_to_eb(self,
                                      mock_get_user_eb_api,
                                      mock_api_post_call,
                                      mock_api_get_call):
        result = post_discount_code_to_eb('TEST', '1', '1', '20')
        mock_api_post_call.assert_called_once()
        self.assertEquals(result['id'], '1')


class UtilsApiDSTest(TestCase):
    @patch('bundesliga_app.utils.request', return_value=MOCK_DS_API_VALID_NUMBER)
    def test_validate_member_number_ds(self, mock_api_call):
        CardId = '1'
        result = validate_member_number_ds(CardId)
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][1]['params']['CardId'],
            CardId,
        )
        self.assertEquals(
            result['Kartentyp'],
            "2"
        )

    @patch('bundesliga_app.utils.request', return_value=MOCK_DS_API_INVALID_REQUEST)
    def test_invalid_validate_member_number_ds(self, mock_api_call):
        CardId = '1'
        result = validate_member_number_ds(CardId)
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][1]['params']['CardId'],
            CardId,
        )
        self.assertEquals(
            result,
            'Invalid Request'
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
        # Create active event of another organizer
        self.events_another_organizer = EventFactory.create_batch(
            4,
            organizer=OrganizerFactory(),  # Random organizer
            is_active=True,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_homepage(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        self.assertEqual(self.response.status_code, 200)

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_home_url_has_index_template(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'index.html',
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_events_organizer(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        for event in self.events:
            self.assertIn(
                event.id,
                self.response.context_data['events']
            )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_events_organizer_not_active(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        self.assertNotContains(
            self.response,
            self.no_active_events,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_events_another_organizer(self, mock_get_event_eb_api):
        self.response = self.client.get('/')
        for event in self.events_another_organizer:
            self.assertNotContains(
                self.response,
                event,
            )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
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

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_event_api_free)
    def test_if_event_is_free_delete_discount(self, mock_get_event_eb_api):
        event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )

        discount = DiscountFactory(
            event=event,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get('/')
        self.assertEqual(
            len(Discount.objects.filter(event=event)),
            0,
        )
        self.assertContains(
            self.response,
            "It doesn't have any paid ticket",
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

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_event_discount(self, mock_get_event_eb_api):
        self.assertEqual(self.response.status_code, 200)

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_event_discount_url_has_correct_template(self, mock_get_event_eb_api):
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/create_discount.html',
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_event_in_response(self, mock_get_event_eb_api):
        self.assertEqual(
            self.response.context_data['event'].id,
            self.event.id,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_wrong_percentage_value_negative(self, mock_get_event_eb_api):
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

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_wrong_percentage_value_too_high(self, mock_get_event_eb_api):
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

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_correct(self, mock_get_event_eb_api):
        self.response = self.client.post(
            '/events_discount/{}/new/'.format(self.event.id),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
            },
        )
        self.assertEqual(
            len(Discount.objects.filter(event=self.event)),
            1,
        )
        self.assertEqual(self.response.status_code, 302)

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_second_discount(self, mock_get_event_eb_api):
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

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_event_api_free)
    def test_create_discount_on_free_event(self, mock_get_event_eb_api):
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
            'You cant create a discount in a free event'
        )


@patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
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

    def test_modify_event_discount(self, mock_get_event_eb_api):
        self.assertEqual(self.response.status_code, 200)

    def test_modify_event_discount_url_has_correct_template(self, mock_get_event_eb_api):
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/create_discount.html',
        )

    def test_event_in_response(self, mock_get_event_eb_api):
        self.assertEqual(
            self.response.context_data['event'].id,
            self.event.id,
        )

    def test_discount_in_response(self, mock_get_event_eb_api):
        self.assertEqual(
            self.response.context_data['discount'].id,
            self.discount.id,
        )

    def test_modify_discount_correct_percentage_value(self, mock_get_event_eb_api):
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

    def test_modify_discount_low_percentage_value(self, mock_get_event_eb_api):

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

    def test_modify_discount_too_high_percentage_value(self, mock_get_event_eb_api):

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
                event['start_date'],
                datetime.datetime(2018, 11, 3, 19, 0),
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

    def test_post_event_update_unselect_with_discount(self,
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
        self.discount = DiscountFactory(
            event=self.event,
        )
        self.response = self.client.post(
            path='/select_events/',
        )
        event_in_db = Event.objects.filter(event_id=event_mock_api_eb['id'])
        discount_in_db = Discount.objects.filter(event=self.event)
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(
            len(event_in_db),
            1,
        )
        self.assertFalse(
            event_in_db.get().is_active
        )
        self.assertEqual(
            len(discount_in_db),
            0,
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
        self.assertEqual(
            permission_denied.exception.args[0],
            "You don't have access to this event",
        )

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
        self.view.response = 'events_discount/{}/{}/'.format(
            event2.id, discount.id)

        with self.assertRaises(PermissionDenied) as permission_denied:
            self.view.get_discount()
        self.assertEqual(
            permission_denied.exception.args[0],
            "You don't have access to this discount"
        )

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
        self.view.response = 'events_discount/{}/{}/'.format(
            event.id, discount.id)
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


@patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
class LandingPageBuyerViewTest(TestCase):
    def setUp(self):
        self.organizer = OrganizerFactory()
        # Create Active Event of organizer
        self.events = EventFactory.create_batch(
            4,
            organizer=self.organizer,
            is_active=True,
        )
        # Create inactive event of organizer
        self.no_active_events = EventFactory(
            organizer=self.organizer,
            is_active=False,
        )
        # Create active event of another organizer
        self.event_another_organizer = EventFactory(
            organizer=OrganizerFactory(),  # Random organizer
            is_active=True,
        )

    def test_landing_page_buyer(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(self.response.status_code, 200)

    def test_landing_page_url_has_index_template(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'buyer/landing_page_buyer.html',
        )

    def test_events_landing_page(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        for event in self.events:
            self.assertIn(
                event.id,
                self.response.context_data['events'],
            )

    def test_events_landing_page_not_active(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertNotIn(
            self.no_active_events.id,
            self.response.context_data['events'],
        )

    def test_events_another_organizer(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertNotIn(
            self.event_another_organizer.id,
            self.response.context_data['events'],
        )

    def test_get_discount_if_exists(self, mock_get_event_eb_api):
        discount = DiscountFactory(
            event=self.events[0],
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(
            self.response.context['events'][self.events[0].id]['discount'],
            discount.value,
        )


@patch('bundesliga_app.views.get_venue_eb_api', return_value=MOCK_VENUE_API)
class ListingPageEventViewTest(TestCase):
    def setUp(self):
        self.organizer = OrganizerFactory()
        # Create active event of organizer
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_free)
    def test_listing_page_event(self,
                                mock_get_venue_eb_api,
                                mock_get_event_eb_api,
                                mock_get_event_tickets_eb_api,
                                ):
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.assertEqual(self.response.status_code, 200)

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_free)
    def test_listing_page_url_has_index_template(self,
                                                 mock_get_venue_eb_api,
                                                 mock_get_event_eb_api,
                                                 mock_get_event_tickets_eb_api,
                                                 ):
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'buyer/listing_page_event.html',
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_free)
    def test_listing_page_event_has_organizer(self,
                                              mock_get_venue_eb_api,
                                              mock_get_event_eb_api,
                                              mock_get_event_tickets_eb_api,
                                              ):

        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.assertEqual(
            self.response.context['organizer'],
            self.organizer,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_free)
    def test_listing_page_event_has_event(self,
                                          mock_get_venue_eb_api,
                                          mock_get_event_eb_api,
                                          mock_get_event_tickets_eb_api,
                                          ):

        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.assertEqual(
            int(self.response.context['event_id']),
            self.event.id,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_free)
    def test_listing_page_event_has_venue(self,
                                          mock_get_venue_eb_api,
                                          mock_get_event_eb_api,
                                          mock_get_event_tickets_eb_api,
                                          ):

        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.assertEqual(
            self.response.context['venue'],
            MOCK_VENUE_API
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_event_api_without_venue)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_free)
    def test_listing_page_event_has_not_venue(self,
                                              mock_get_venue_eb_api,
                                              mock_get_event_eb_api,
                                              mock_get_event_tickets_eb_api,
                                              ):

        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.assertEqual(
            self.response.context['venue'],
            None
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_free)
    def test_get_discount_if_exists(self,
                                    mock_get_venue_eb_api,
                                    mock_get_event_eb_api,
                                    mock_get_event_tickets_eb_api,
                                    ):
        discount = DiscountFactory(
            event=self.event,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.assertEqual(
            self.response.context['event']['discount'],
            discount.value,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_free)
    def test_get_tickets_free_event(self,
                                    mock_get_venue_eb_api,
                                    mock_get_event_eb_api,
                                    mock_get_event_tickets_eb_api,
                                    ):
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        ticket_values = {
            'min_value': None,
            'min_value_display': None,
            'max_value': None,
            'max_value_display': None,
        }
        self.assertEqual(
            self.response.context['tickets'],
            ticket_values,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=MOCK_EVENT_TICKETS)
    def test_get_tickets_paid_and_free_event(self,
                                             mock_get_venue_eb_api,
                                             mock_get_event_eb_api,
                                             mock_get_event_tickets_eb_api,
                                             ):
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        ticket_values = {
            'min_value': 0,
            'min_value_display': "$0.00",
            'max_value': 300.00,
            'max_value_display': "$300.00",
        }
        self.assertEqual(
            self.response.context['tickets'],
            ticket_values,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_paid)
    def test_get_tickets_paid_event(self,
                                    mock_get_venue_eb_api,
                                    mock_get_event_eb_api,
                                    mock_get_event_tickets_eb_api,
                                    ):
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        ticket_values = {
            'min_value': 20.0,
            'min_value_display': "$20.00",
            'max_value': 300.00,
            'max_value_display': "$300.00",
        }
        self.assertEqual(
            self.response.context['tickets'],
            ticket_values,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', side_effect=get_mock_event_tickets_api_paid_inverse_position)
    def test_get_tickets_paid_event_inverse_position(self,
                                                     mock_get_venue_eb_api,
                                                     mock_get_event_eb_api,
                                                     mock_get_event_tickets_eb_api,
                                                     ):
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        ticket_values = {
            'min_value': 20.0,
            'min_value_display': "$20.00",
            'max_value': 300.00,
            'max_value_display': "$300.00",
        }
        self.assertEqual(
            self.response.context['tickets'],
            ticket_values,
        )


class GetDiscountFormTest(TestCase):

    def test_invalid_form_is_empty(
            self,
    ):
        form = GetDiscountForm()
        result = form.is_valid()
        self.assertFalse(result)

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_VALID_NUMBER.text,
    )
    def test_valid_member_number(
            self,
            mock_validate_member_number_ds):
        form = GetDiscountForm({
            'member_number': '1234',
        })
        result = form.is_valid()
        self.assertTrue(result)

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_INVALID_NUMBER.text,
    )
    def test_invalid_member_number(
            self,
            mock_validate_member_number_ds):
        form = GetDiscountForm({
            'member_number': '1234',
        })
        result = form.is_valid()
        self.assertFalse(result)

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value='Invalid Request',
    )
    def test_invalid_request(
            self,
            mock_validate_member_number_ds):
        form = GetDiscountForm({
            'member_number': '1234',
        })
        result = form.is_valid()
        self.assertFalse(result)


@patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
class GetDiscountViewTest(TestCase):
    def setUp(self):
        self.organizer = OrganizerFactory()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        self.events_discount = DiscountFactory(
            event=self.event,
        )

    def test_event_in_context(self, mock_get_event_eb_api):
        self.response = self.client.get('/landing_page/{}/event/{}/get_discount/'.format(
            self.organizer.id,
            self.event.id)
        )

        self.assertContains(
            self.response,
            self.event.id
        )

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_VALID_NUMBER.text,
    )
    @patch(
        'bundesliga_app.views.check_discount_code_in_eb',
        return_value=MOCK_DISCOUNT_DOESNT_EXIST_IN_EB,
    )
    @patch(
        'bundesliga_app.views.post_discount_code_to_eb',
        return_value=MOCK_POST_DISCOUNT_CODE_TO_EB,
    )
    @patch(
        'bundesliga_app.utils.get_user_eb_api',
        return_value=MOCK_USER_API,
    )
    def test_post_get_discount(self,
                               mock_get_event_eb_api,
                               mock_validate_member_number_ds,
                               mock_check_discount_code_in_eb,
                               mock_post_discount_code_to_eb,
                               mock_get_user_eb_api):
        self.response = self.client.get('/landing_page/{}/event/{}/get_discount/'.format(
            self.organizer.id,
            self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/get_discount/'.format(
                self.organizer.id,
                self.event.id
            ),
            {
                'member_number': '12345'
            }
        )
        self.assertEqual(self.response.status_code, 302)

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_VALID_NUMBER.text,
    )
    @patch(
        'bundesliga_app.views.check_discount_code_in_eb',
        return_value=MOCK_DISCOUNT_EXISTS_IN_EB_NO_USAGE,
    )
    @patch(
        'bundesliga_app.views.post_discount_code_to_eb',
        return_value=MOCK_POST_DISCOUNT_CODE_TO_EB,
    )
    @patch(
        'bundesliga_app.utils.get_user_eb_api',
        return_value=MOCK_USER_API,
    )
    def test_post_existing_discount_code(self, mock_get_event_eb_api,
                                         mock_validate_member_number_ds,
                                         mock_check_discount_code_in_eb,
                                         mock_post_discount_code_to_eb,
                                         mock_get_user_eb_api):
        self.response = self.client.get('/landing_page/{}/event/{}/get_discount/'.format(
            self.organizer.id,
            self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/get_discount/'.format(
                self.organizer.id,
                self.event.id
            ),
            {
                'member_number': '12345'
            }
        )
        self.assertEqual(self.response.status_code, 302)

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_VALID_NUMBER.text,
    )
    @patch(
        'bundesliga_app.views.check_discount_code_in_eb',
        return_value=MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE,
    )
    @patch(
        'bundesliga_app.views.post_discount_code_to_eb',
        return_value=MOCK_POST_DISCOUNT_CODE_TO_EB,
    )
    @patch(
        'bundesliga_app.utils.get_user_eb_api',
        return_value=MOCK_USER_API,
    )
    def test_post_existing_discount_code_with_usage(self, mock_get_event_eb_api,
                                                    mock_validate_member_number_ds,
                                                    mock_check_discount_code_in_eb,
                                                    mock_post_discount_code_to_eb,
                                                    mock_get_user_eb_api):
        self.response = self.client.get('/landing_page/{}/event/{}/get_discount/'.format(
            self.organizer.id,
            self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/get_discount/'.format(
                self.organizer.id,
                self.event.id
            ),
            {
                'member_number': '12345'
            }
        )
        self.assertEqual(self.response.status_code, 200)

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_INVALID_NUMBER.text,
    )
    @patch(
        'bundesliga_app.views.check_discount_code_in_eb',
        return_value=MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE,
    )
    @patch(
        'bundesliga_app.views.post_discount_code_to_eb',
        return_value=MOCK_POST_DISCOUNT_CODE_TO_EB,
    )
    @patch(
        'bundesliga_app.utils.get_user_eb_api',
        return_value=MOCK_USER_API,
    )
    def test_post_invalid_form(self, mock_get_event_eb_api,
                               mock_validate_member_number_ds,
                               mock_check_discount_code_in_eb,
                               mock_post_discount_code_to_eb,
                               mock_get_user_eb_api):
        self.response = self.client.get('/landing_page/{}/event/{}/get_discount/'.format(
            self.organizer.id,
            self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/get_discount/'.format(
                self.organizer.id,
                self.event.id
            ),
            {
                'member_number': '12345'
            }
        )
        self.assertEqual(self.response.status_code, 200)
