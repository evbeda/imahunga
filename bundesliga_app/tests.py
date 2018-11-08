from django.test import (
    TestCase,
    RequestFactory,
)
from .factories import (
    AuthFactory,
    DiscountCodeFactory,
    EventFactory,
    EventDiscountFactory,
    EventTicketTypeFactory,
    MemberDiscountCodeFactory,
    OrganizerFactory,
    TicketTypeDiscountFactory,
)
from django.views.generic.base import TemplateView
from mock import patch
from django.apps import apps
from urllib.parse import urlencode
from bundesliga_app.apps import BundesligaAppConfig
from bundesliga_app.utils import (
    EventAccessMixin,
    DiscountAccessMixin,
    check_discount_code_in_eb,
    get_auth_token,
    get_user_eb_api,
    get_events_user_eb_api,
    get_event_eb_api,
    get_venue_eb_api,
    get_event_tickets_eb_api,
    post_ticket_discount_code_to_eb,
    post_event_discount_code_to_eb,
    validate_member_number_ds,
)
from .models import (
    DiscountCode,
    DiscountType,
    EventDiscount,
    Event,
    EventTicketType,
    MemberDiscountCode,
    StatusMemberDiscountCode,
    TicketTypeDiscount,
)
from bundesliga_app.mocks import (
    MOCK_DISCOUNT_EXISTS_IN_EB_MULTIPLE_USAGES,
    MOCK_DISCOUNT_EXISTS_IN_EB_MULTIPLE_USAGES_ONE_USED,
    MOCK_DISCOUNT_EXISTS_IN_EB_ONE_USE_NOT_USED,
    MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE,
    MOCK_DS_API_VALID_NUMBER,
    MOCK_DS_API_INVALID_NUMBER,
    MOCK_DS_API_INVALID_REQUEST,
    MOCK_EVENT_TICKETS,
    MOCK_LIST_EVENTS_API,
    MOCK_USER_API,
    MOCK_VENUE_API,
    MOCK_UPDATE_DISCOUNT_CODE_TO_EB_USES_LEFT,
    MOCK_UPDATE_DISCOUNT_CODE_TO_EB,
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
from django.conf import settings


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
        setattr(settings, "CACHES", {
            'default': {
                'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
            }
        })
        setattr(settings, "CACHE_TTL", 0)
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


@patch('bundesliga_app.utils.Eventbrite.get', return_value={})
class UtilsApiEBTest(TestCase):

    def test_get_user_eb_api(self, mock_api_call):
        get_user_eb_api('TEST')
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][0][0],
            '/users/me/',
        )

    def test_get_events_user_eb_api(self, mock_api_call):
        mock_api_call.return_value = {'events':''}
        get_events_user_eb_api('TEST')
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][0][0],
            '/users/me/owned_events/?status=live',
        )

    def test_get_event_eb_api(self, mock_api_call):
        with self.settings(
                CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}},
                CACHE_TTL=0,
            ):
            mock_api_call.return_value = {'id': 1}
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
        mock_api_call.return_value = {'ticket_classes':''}
        get_event_tickets_eb_api('TEST', '1')
        mock_api_call.assert_called_once()
        self.assertEquals(
            mock_api_call.call_args_list[0][0][0],
            '/events/1/ticket_classes/',
        )

    @patch('bundesliga_app.utils.get_user_eb_api', return_value=MOCK_USER_API)
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE)
    @patch('bundesliga_app.utils.get_auth_token', return_value={})
    def test_check_discount_code_in_eb(self,
                                       mock_get_auth_token,
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
    @patch('bundesliga_app.utils.get_auth_token', return_value={})
    def test_post_ticket_discount_code_to_eb(
        self,
        mock_get_auth_token,
        mock_get_user_eb_api,
        mock_api_post_call,
        mock_api_get_call
    ):
        mock_api_get_call.return_value = {'id': 1}
        result = post_ticket_discount_code_to_eb('TEST', '1', '1', '20', '1', '1')
        mock_api_post_call.assert_called_once()
        self.assertEquals(result['id'], '1')

    @patch('bundesliga_app.utils.Eventbrite.post', return_value={'id': '1'})
    @patch('bundesliga_app.views.get_user_eb_api', return_value=MOCK_USER_API)
    @patch('bundesliga_app.utils.get_auth_token', return_value={})
    def test_post_event_discount_code_to_eb(
        self,
        mock_get_auth_token,
        mock_get_user_eb_api,
        mock_api_post_call,
        mock_api_get_call
    ):
        mock_api_get_call.return_value = {'id': 1}
        result = post_event_discount_code_to_eb('TEST', '1', '1', '20', '1')
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
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_homepage(self,
                      mock_get_event_tickets_eb_api,
                      mock_get_event_eb_api,
                      ):
        # Create 1 Ticket Type for the first event
        self.tickets_type = EventTicketTypeFactory(
            event=self.events[0],
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get('/')
        self.assertEqual(self.response.status_code, 200)

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_home_url_has_index_template(self,
                                         mock_get_event_tickets_eb_api,
                                         mock_get_event_eb_api,
                                         ):
        self.response = self.client.get('/')
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'index.html',
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_events_organizer(self,
                              mock_get_event_tickets_eb_api,
                              mock_get_event_eb_api,
                              ):
        self.response = self.client.get('/')
        for event in self.events:
            self.assertIn(
                event.id,
                self.response.context_data['events']
            )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_events_organizer_not_active(self,
                                         mock_get_event_tickets_eb_api,
                                         mock_get_event_eb_api,
                                         ):
        self.response = self.client.get('/')
        self.assertNotContains(
            self.response,
            self.no_active_events,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_events_another_organizer(self,
                                      mock_get_event_tickets_eb_api,
                                      mock_get_event_eb_api,
                                      ):
        self.response = self.client.get('/')
        for event in self.events_another_organizer:
            self.assertNotContains(
                self.response,
                event,
            )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_get_discount_ticket_if_exists(self,
                                    mock_get_event_tickets_eb_api,
                                    mock_get_event_eb_api,
                                    ):
        # Create 1 Ticket Type for the first event
        self.tickets_type = EventTicketTypeFactory(
            event=self.events[0],
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=self.tickets_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get('/')
        self.assertEqual(
            discount.id,
            self.response.context['events'][self.events[0].id]['tickets_type'][
                str(self.tickets_type.id)]['discount']['id']
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_get_discount_event_if_exists(self,
                                          mock_get_event_tickets_eb_api,
                                          mock_get_event_eb_api,
                                          ):
        EventDiscountFactory(
            event=self.events[0],
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get('/')
        self.assertTrue(
            self.response.context['events'][self.events[0].id]['has_discount']
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_event_api_free)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_if_event_is_free_delete_discount(self,
                                              mock_get_event_tickets_eb_api,
                                              mock_get_event_eb_api):
        event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        # Create 1 Ticket Type for the event
        tickets_type = EventTicketTypeFactory(
            event=event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=tickets_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get('/')
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=tickets_type)),
            0,
        )
        self.assertEqual(
            len(EventTicketType.objects.filter(event=event)),
            0,
        )
        self.assertContains(
            self.response,
            "It doesn't have any paid ticket",
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=MOCK_EVENT_TICKETS[0])
    def test_free_ticket_type_delete_discount(self,
                                              mock_get_event_tickets_eb_api,
                                              mock_get_event_eb_api):
        event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        # Create 1 Ticket Type for the event
        tickets_type = EventTicketTypeFactory(
            event=event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=tickets_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get('/')
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=tickets_type)),
            0,
        )
        self.assertEqual(
            len(EventTicketType.objects.filter(event=event)),
            1,
        )


@patch('bundesliga_app.views.get_event_tickets_eb_api', return_value=MOCK_EVENT_TICKETS[0])
@patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
class EventDiscountsViewTest(TestBase):
    def setUp(self):
        super(EventDiscountsViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )

    def test_event_discounts(self,
                             mock_get_event_eb_api,
                             mock_get_event_tickets_eb_api):
        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertEqual(self.response.status_code, 200)

    def test_event_discounts_url_has_correct_template(self,
                                                      mock_get_event_eb_api,
                                                      mock_get_event_tickets_eb_api):
        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/event_discounts.html',
        )

    def test_event_in_response(self,
                               mock_get_event_eb_api,
                               mock_get_event_tickets_eb_api):
        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
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

    def test_events_ticket_type_discounts_in_response(self,
                                                      mock_get_event_eb_api,
                                                      mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertEqual(
            ticket_type.ticket_id_eb,
            self.response.context_data['tickets_type'][str(
                ticket_type.id)]['id'],
        )

    def test_events_discount_in_response(self,
                                         mock_get_event_eb_api,
                                         mock_get_event_tickets_eb_api):
        discount = EventDiscountFactory(
            event=self.event,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertEqual(
            discount.id,
            self.response.context_data['event_discount'].id,
        )

    def test_events_ticket_type_delete(self,
                                       mock_get_event_eb_api,
                                       mock_get_event_tickets_eb_api):
        # Ticket type with random ticket_eb_ids
        ticket_type = EventTicketTypeFactory(
            event=self.event,
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertEqual(
            len(EventTicketType.objects.filter(id=ticket_type.id)),
            0,
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            0,
        )

    def test_events_ticket_type_free_delete_discount(self,
                                                     mock_get_event_eb_api,
                                                     mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/'.format(self.event.id)
        )
        self.assertEqual(
            ticket_type.ticket_id_eb,
            self.response.context_data['tickets_type'][str(
                ticket_type.id)]['id'],
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            0,
        )


class CreateDiscountEventViewTest(TestBase):
    def setUp(self):
        super(CreateDiscountEventViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        self.discount_type_event = DiscountType.objects.get(
            name='Event'
        )
        self.discount_type_ticket = DiscountType.objects.get(
            name='Ticket Type'
        )

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_event_discount(self,
                                   mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        self.assertEqual(self.response.status_code, 200)

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_event_discount_url_has_correct_template(self,
                                                            mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/create_discount_event.html',
        )

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_event_in_response(self,
                                               mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        self.assertEqual(
            self.response.context_data['event'].id,
            self.event.id,
        )

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_wrong_percentage_value_negative(self,
                                                             mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            ),
            {
                'discount_name': 'discount',
                'discount_type': 'percentage',
                'discount_value': -50,
            },
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(
            self.response,
            'Ensure this value is greater than or equal to 1.'
        )
        self.assertEqual(
            len(EventDiscount.objects.filter(event=self.event)),
            0,
        )

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_wrong_percentage_value_too_high(self,
                                                             mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            ),
            {
                'discount_name': 'discount',
                'discount_type': 'percentage',
                'discount_value': 200,
            },
        )
        self.assertContains(
            self.response,
            'Ensure this value is less than or equal to 100.'
        )
        self.assertEqual(
            len(EventDiscount.objects.filter(event=self.event)),
            0,
        )

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_event_discount_correct(self,
                                           mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            ),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
            },
        )

        self.assertEqual(
            len(EventDiscount.objects.filter(event=self.event)),
            1,
        )
        self.assertEqual(self.response.status_code, 302)

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_correct_delete_other_discounts(self,
                                                            mock_get_event_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            discount_type=self.discount_type_ticket,
        )
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            ),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
            },
        )

        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            0,
        )
        self.assertEqual(self.response.status_code, 302)

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_second_discount(self,
                                    mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        EventDiscountFactory(
            event=self.event,
            discount_type=self.discount_type_event,
        )
        self.response = self.client.post(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            ),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
            },
        )
        self.assertContains(
            self.response,
            'You already have a discount for this event')

    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_event_api_free)
    def test_create_discount_on_free_event(self,
                                           mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/event/new/'.format(
                self.event.id,
            ),
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

@patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
class ModifyDiscountEventViewTest(TestBase):
    def setUp(self):
        super(ModifyDiscountEventViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        self.discount_type_event = DiscountType.objects.get(
            name='Event'
        )
        self.discount_type_ticket = DiscountType.objects.get(
            name='Ticket Type'
        )
        self.discount = EventDiscountFactory(
            event=self.event,
            value=100.0,
            value_type="percentage",
            discount_type=self.discount_type_event,
        )

    def test_modify_event_discount(self,
                                   mock_get_event_eb_api):

        self.response = self.client.get(
            '/events_discount/{}/event/{}/'.format(
                self.event.id,
                self.discount.id,
            )
        )
        self.assertEqual(self.response.status_code, 200)

    def test_modify_event_discount_url_has_correct_template(self,
                                                            mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/{}/'.format(
                self.event.id,
                self.discount.id,
            )
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/create_discount_event.html',
        )

    def test_event_in_response(self,
                               mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/{}/'.format(
                self.event.id,
                self.discount.id,
            )
        )
        self.assertEqual(
            self.response.context_data['event'].id,
            self.event.id,
        )

    def test_event_discount_in_response(self,
                                  mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/{}/'.format(
                self.event.id,
                self.discount.id,
            )
        )
        self.assertEqual(
            self.response.context_data['discount'].id,
            self.discount.id,
        )

    def test_modify_discount_correct_percentage_value(self,
                                                      mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/{}/'.format(
                self.event.id,
                self.discount.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/event/{}/'.format(
                self.event.id,
                self.discount.id,
            ),
            {
                'discount_name': self.discount.name,
                'discount_type': 'percentage',
                'discount_value': 20,
            },
        )
        updated_discount = EventDiscount.objects.get(id=self.discount.id)
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(updated_discount.value_type, 'percentage')
        self.assertEqual(updated_discount.value, 20)
        self.assertEqual(
            len(EventDiscount.objects.filter(event=self.event)),
            1,
        )

    def test_modify_discount_low_percentage_value(self,
                                                  mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/{}/'.format(
                self.event.id,
                self.discount.id,
            )
        )

        self.response = self.client.post(
            '/events_discount/{}/event/{}/'.format(
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
            'Ensure this value is greater than or equal to 1.'
        )
        self.assertEqual(
            len(EventDiscount.objects.filter(event=self.event)),
            1,
        )

    def test_modify_discount_too_high_percentage_value(self,
                                                       mock_get_event_eb_api):
        self.response = self.client.get(
            '/events_discount/{}/event/{}/'.format(
                self.event.id,
                self.discount.id,
            )
        )

        self.response = self.client.post(
            '/events_discount/{}/event/{}/'.format(
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
            len(EventDiscount.objects.filter(event=self.event)),
            1,
        )


class CreateDiscountTicketTypeViewTest(TestBase):
    def setUp(self):
        super(CreateDiscountTicketTypeViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        self.discount_type_event = DiscountType.objects.get(
            name='Event'
        )

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_event_discount(self,
                                   mock_get_event_eb_api,
                                   mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.assertEqual(self.response.status_code, 200)

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_event_discount_url_has_correct_template(self,
                                                            mock_get_event_eb_api,
                                                            mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/create_discount_ticket_type.html',
        )

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_event_in_response(self,
                               mock_get_event_eb_api,
                               mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.assertEqual(
            self.response.context_data['event'].id,
            self.event.id,
        )

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_ticket_type_in_response(self,
                                     mock_get_event_eb_api,
                                     mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.assertEqual(
            self.response.context_data['ticket_type'][str(
                ticket_type.id)]['id'],
            ticket_type.ticket_id_eb,
        )

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_wrong_percentage_value_negative(self,
                                                             mock_get_event_eb_api,
                                                             mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            ),
            {
                'discount_name': 'discount',
                'discount_type': 'percentage',
                'discount_value': -50,
            },
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(
            self.response,
            'Ensure this value is greater than or equal to 1.'
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            0,
        )

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_wrong_percentage_value_too_high(self,
                                                             mock_get_event_eb_api,
                                                             mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            ),
            {
                'discount_name': 'discount',
                'discount_type': 'percentage',
                'discount_value': 200,
            },
        )
        self.assertContains(
            self.response,
            'Ensure this value is less than or equal to 100.'
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            0,
        )

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_correct(self,
                                     mock_get_event_eb_api,
                                     mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            ),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
                'ticket_type': mock_get_event_tickets_eb_api.return_value[0]['name'],
            },
        )

        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            1,
        )
        self.assertEqual(self.response.status_code, 302)

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_correct_delete_other_discounts(self,
                                                            mock_get_event_eb_api,
                                                            mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        EventDiscountFactory(
            event=self.event,
            discount_type=self.discount_type_event,
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            ),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
                'ticket_type': mock_get_event_tickets_eb_api.return_value[0]['name'],
            },
        )

        self.assertEqual(
            len(EventDiscount.objects.filter(event=self.event)),
            0,
        )
        self.assertEqual(self.response.status_code, 302)


    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_second_discount(self,
                                    mock_get_event_eb_api,
                                    mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            ),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
                'ticket_type': mock_get_event_tickets_eb_api.return_value[0]['name'],
            },
        )
        self.assertContains(
            self.response,
            'You have already used a discount for this ticket')

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_event_api_free)
    def test_create_discount_on_free_event(self,
                                           mock_get_event_eb_api,
                                           mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            ),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
                'ticket_type': mock_get_event_tickets_eb_api.return_value[0]['name'],
            },
        )

        self.assertContains(
            self.response,
            'You can not create a discount in a free event'
        )

    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=MOCK_EVENT_TICKETS[0])
    @patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
    def test_create_discount_on_free_ticket(self,
                                            mock_get_event_eb_api,
                                            mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/new/'.format(
                self.event.id,
                ticket_type.id,
            ),
            {
                'discount_name': 'descuento',
                'discount_type': 'percentage',
                'discount_value': 50,
                'ticket_type': mock_get_event_tickets_eb_api.return_value[0]['name'],
            },
        )

        self.assertContains(
            self.response,
            'You can not create a discount for a free ticket'
        )


@patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
@patch('bundesliga_app.forms.get_event_eb_api', side_effect=get_mock_events_api)
class ModifyDiscountTicketTypeViewTest(TestBase):
    def setUp(self):
        super(ModifyDiscountTicketTypeViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )

    def test_modify_event_discount(self,
                                   mock_get_event_eb_api,
                                   mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            )
        )
        self.assertEqual(self.response.status_code, 200)

    def test_modify_event_discount_url_has_correct_template(self,
                                                            mock_get_event_eb_api,
                                                            mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            )
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'organizer/create_discount_ticket_type.html',
        )

    def test_event_in_response(self,
                               mock_get_event_eb_api,
                               mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            )
        )
        self.assertEqual(
            self.response.context_data['event'].id,
            self.event.id,
        )

    def test_discount_in_response(self,
                                  mock_get_event_eb_api,
                                  mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            )
        )
        self.assertEqual(
            self.response.context_data['discount'].id,
            discount.id,
        )

    def test_modify_discount_correct_percentage_value(self,
                                                      mock_get_event_eb_api,
                                                      mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            )
        )
        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            ),
            {
                'discount_name': discount.name,
                'discount_type': 'percentage',
                'discount_value': 20,
                'ticket_type': mock_get_event_tickets_eb_api.return_value[0]['name'],
            },
        )
        updated_discount = TicketTypeDiscount.objects.get(id=discount.id)
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(updated_discount.value_type, 'percentage')
        self.assertEqual(updated_discount.value, 20)
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            1,
        )

    def test_modify_discount_low_percentage_value(self,
                                                  mock_get_event_eb_api,
                                                  mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            )
        )

        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            ),
            {
                'discount_name': discount.name,
                'discount_type': 'percentage',
                'discount_value': -10,
                'ticket_type': mock_get_event_tickets_eb_api.return_value[0]['name'],
            },
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(
            self.response,
            'Ensure this value is greater than or equal to 1.'
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            1,
        )

    def test_modify_discount_too_high_percentage_value(self,
                                                       mock_get_event_eb_api,
                                                       mock_get_event_tickets_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            )
        )

        self.response = self.client.post(
            '/events_discount/{}/ticket_type/{}/{}/'.format(
                self.event.id,
                ticket_type.id,
                discount.id,
            ),
            {
                'discount_name': discount.name,
                'discount_type': 'percentage',
                'discount_value': 150,
                'ticket_type': mock_get_event_tickets_eb_api.return_value[0]['name'],
            },
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(
            self.response,
            'Ensure this value is less than or equal to 100.'
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            1,
        )


class DeleteDiscountViewTest(TestBase):
    def setUp(self):
        super(DeleteDiscountViewTest, self).setUp()
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        self.ticket_type = EventTicketTypeFactory(
            event=self.event,
        )

        self.discount = TicketTypeDiscountFactory(
            ticket_type=self.ticket_type,
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
            len(TicketTypeDiscount.objects.filter(ticket_type=self.ticket_type)),
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

    @patch('bundesliga_app.views.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_post_event_new(self,
                            mock_get_event_tickets_eb_api,
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

    @patch('bundesliga_app.views.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_post_event_update(self,
                               mock_get_event_tickets_eb_api,
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

    @patch('bundesliga_app.views.get_event_tickets_eb_api', return_value=MOCK_EVENT_TICKETS[0])
    def test_post_event_update_free_ticket(self,
                                           mock_get_event_tickets_eb_api,
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
        self.ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        self.discount = TicketTypeDiscountFactory(
            ticket_type=self.ticket_type,
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
        self.assertEqual(
            len(EventTicketType.objects.filter(
                ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id'])
                ),
            1,
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(
                ticket_type=self.ticket_type)
                ),
            0,
        )

    @patch('bundesliga_app.views.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_post_event_update_delete_old_ticket(self,
                                                 mock_get_event_tickets_eb_api,
                                                 mock_get_events_user_eb_api,
                                                 mock_get_user_eb_api,
                                                 ):
        event_mock_api_eb = mock_get_events_user_eb_api.return_value[0]
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
            event_id=event_mock_api_eb['id'],
        )
        """ in one hand create the ticket type with the ticket 0 from the mock
        in another hand, the patch will return the other tickets so
        when the view calls get_event_tickets_eb_api
        it will return the ticket 1 and 2 but not the 0"""
        self.ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=MOCK_EVENT_TICKETS[0][0]['id']
        )
        self.discount = TicketTypeDiscountFactory(
            ticket_type=self.ticket_type,
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
        self.assertEqual(
            len(EventTicketType.objects.filter(
                ticket_id_eb=self.ticket_type.ticket_id_eb)
                ),
            0,
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(
                ticket_type=self.ticket_type)
                ),
            0,
        )

    @patch('bundesliga_app.views.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_post_event_update_delete_event_discount(self,
                                                     mock_get_event_tickets_eb_api,
                                                     mock_get_events_user_eb_api,
                                                     mock_get_user_eb_api,
                                                     ):
        event_mock_api_eb = mock_get_events_user_eb_api.return_value[0]
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
            event_id=event_mock_api_eb['id'],
        )
        self.discount = EventDiscountFactory(
            event=self.event,
        )
        self.response = self.client.post(
            path='/select_events/',
        )
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(
            len(Event.objects.filter(event_id=event_mock_api_eb['id'])),
            1,
        )
        self.assertEqual(
            len(EventDiscount.objects.filter(
                event=self.event)
                ),
            0,
        )

    def test_post_event_update_unselect(self,
                                        mock_get_events_user_eb_api,
                                        mock_get_user_eb_api,
                                        ):
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

    def test_post_event_update_unselect_without_discount_and_ticket_type(self,
                                                                         mock_get_events_user_eb_api,
                                                                         mock_get_user_eb_api,
                                                                         ):
        event_mock_api_eb = mock_get_events_user_eb_api.return_value[0]
        self.event = EventFactory(
            organizer=self.organizer,
            is_active=True,
            event_id=event_mock_api_eb['id'],
        )
        self.ticket_type = EventTicketTypeFactory(
            event=self.event
        )
        self.discount = TicketTypeDiscountFactory(
            ticket_type=self.ticket_type,
        )
        self.response = self.client.post(
            path='/select_events/',
        )
        event_in_db = Event.objects.filter(event_id=event_mock_api_eb['id'])
        event_ticket_type_in_db = EventTicketType.objects.filter(
            event=self.event)
        discount_in_db = TicketTypeDiscount.objects.filter(
            ticket_type=self.ticket_type)
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(
            len(event_in_db),
            1,
        )
        self.assertFalse(
            event_in_db.get().is_active
        )
        self.assertEqual(
            len(event_ticket_type_in_db),
            0,
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
        self.discount_type_ticket = DiscountType.objects.get(
            name='Ticket Type'
        )
        self.discount_type_event = DiscountType.objects.get(
            name='Event'
        )

    def test_raise_exception_ticket_discount_permission_denied(self):
        event = EventFactory(
            organizer=OrganizerFactory(),
            is_active=True,
        )
        event2 = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        ticket_type = EventTicketTypeFactory(
            event=event,
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            discount_type=self.discount_type_ticket,
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

        event_ticket_type = EventTicketTypeFactory(
            event=event
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=event_ticket_type,
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
        self.assertEqual(
            self.view.get_discount(),
            discount.discount_ptr,
        )

    def test_raise_exception_event_discount_permission_denied(self):
        event = EventFactory(
            organizer=OrganizerFactory(),
            is_active=True,
        )
        event2 = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        discount = EventDiscountFactory(
            event=event,
            discount_type=self.discount_type_event,
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

    def test_invalid_discount_event(self):
        event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        event2 = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        discount = EventDiscountFactory(
            event=event,
            discount_type=self.discount_type_event,
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
            "This discount does not match with the event"
        )

    def test_invalid_ticket_discount_event(self):
        event = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        event2 = EventFactory(
            organizer=self.organizer,
            is_active=True,
        )
        event_ticket_type = EventTicketTypeFactory(
            event=event
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=event_ticket_type,
            discount_type=self.discount_type_ticket,
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
            "This discount does not match with the event"
        )

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

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_landing_page_buyer(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(self.response.status_code, 200)

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_landing_page_url_has_index_template(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(
            self.response.context_data['view'].template_name,
            'buyer/landing_page_buyer.html',
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_events_landing_page(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        for event in self.events:
            self.assertIn(
                event.id,
                self.response.context_data['events'],
            )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_events_landing_page_not_active(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertNotIn(
            self.no_active_events.id,
            self.response.context_data['events'],
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    def test_events_another_organizer(self, mock_get_event_eb_api):
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertNotIn(
            self.event_another_organizer.id,
            self.response.context_data['events'],
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_get_discount_event(self,
                                mock_get_event_tickets_eb_api,
                                mock_get_event_eb_api):
        discount = EventDiscountFactory(
            event=self.events[0],
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(
            self.response.context['events'][self.events[0].id]['discounts'][discount.id]['id'],
            discount.id,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_get_discount_if_exists_2(self,
                                      mock_get_event_tickets_eb_api,
                                      mock_get_event_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.events[0],
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(
            self.response.context['events'][self.events[0].id]['discounts'][discount.id]['id'],
            discount.id,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_get_discount_if_exists_3(self,
                                      mock_get_event_tickets_eb_api,
                                      mock_get_event_eb_api):
        ticket_type_1 = EventTicketTypeFactory(
            event=self.events[0],
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        ticket_type_2 = EventTicketTypeFactory(
            event=self.events[0],
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        ticket_type_3 = EventTicketTypeFactory(
            event=self.events[0],
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[2]['id']
        )
        discount_1 = TicketTypeDiscountFactory(
            ticket_type=ticket_type_1,
            value=30.0,
            value_type="percentage",
        )
        discount_2 = TicketTypeDiscountFactory(
            ticket_type=ticket_type_2,
            value=80.0,
            value_type="percentage",
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type_3,
            value=40.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(
            self.response.context['events'][self.events[0].id]['max_discount'],
            discount_2.value,
        )
        self.assertEqual(
            self.response.context['events'][self.events[0].id]['min_discount'],
            discount_1.value,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_event_api_free)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_event_free_no_discount(self,
                                    mock_get_event_tickets_eb_api,
                                    mock_get_event_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.events[0],
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/landing_page/{}/'.format(self.organizer.id)
        )
        self.assertEqual(
            len(EventTicketType.objects.filter(event=self.events[0])),
            0,
        )
        self.assertEqual(
            len(TicketTypeDiscount.objects.filter(ticket_type=ticket_type)),
            0,
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
        self.used_status = StatusMemberDiscountCode.objects.get(
            name='Used'
        )
        self.unknown_status = StatusMemberDiscountCode.objects.get(
            name='Unknown'
        )
        self.canceled_status = StatusMemberDiscountCode.objects.get(
            name='Canceled'
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
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_get_discount_if_exists_3(self,
                                      mock_get_event_tickets_eb_api,
                                      mock_get_event_eb_api,
                                      mock_get_venue_eb_api,
                                      ):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type,
            value=100.0,
            value_type="percentage",
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.assertEqual(
            self.response.context['tickets_type'][str(
                ticket_type.id)]['discount']['value'],
            discount.value,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_free())
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
            self.response.context['tickets_value'],
            ticket_values,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=MOCK_EVENT_TICKETS[0])
    def test_get_tickets_paid_and_free_event(self,
                                             mock_get_event_tickets_eb_api,
                                             mock_get_event_eb_api,
                                             mock_get_venue_eb_api,
                                             ):

        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        ticket_values = {
            'min_value': 0,
            'min_value_display': "$0.00",
            'max_value': 20.00,
            'max_value_display': "$20.00",
        }
        self.assertEqual(
            self.response.context['tickets_value'],
            ticket_values,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    def test_get_tickets_paid_event(self,
                                    mock_get_event_tickets_eb_api,
                                    mock_get_event_eb_api,
                                    mock_get_venue_eb_api,
                                    ):

        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
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
            self.response.context['tickets_value'],
            ticket_values,
        )

    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid_inverse_position())
    def test_get_tickets_paid_event_inverse_position(self,
                                                     mock_get_event_tickets_eb_api,
                                                     mock_get_venue_eb_api,
                                                     mock_get_event_eb_api,
                                                     ):
        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[0]['id']
        )

        EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
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
            self.response.context['tickets_value'],
            ticket_values,
        )

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_VALID_NUMBER.text,
    )
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    def test_valid_member_number_ticket_discount(
            self,
            mock_post_ticket_discount_code_to_eb,
            mock_get_event_tickets_eb_api,
            mock_get_event_eb_api,
            mock_validate_member_number_ds,
            mock_get_venue_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567'
            },
        )

        self.assertEqual(self.response.status_code, 200)
        member_discount_code = MemberDiscountCode.objects.filter(
            member_number='1234'
        )
        self.assertEqual(
            len(member_discount_code),
            1
        )

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_VALID_NUMBER.text,
    )
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    def test_post_without_captcha(
            self,
            mock_post_ticket_discount_code_to_eb,
            mock_get_event_tickets_eb_api,
            mock_get_event_eb_api,
            mock_validate_member_number_ds,
            mock_get_venue_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': ''
            },
        )

        self.assertContains(
            self.response,
            "Please complete captcha"
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_INVALID_NUMBER.text,)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    def test_invalid_member_number(
        self,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        self.assertEqual(self.response.status_code, 200)
        member_discount_code = MemberDiscountCode.objects.filter(
            member_number='1234'
        )
        self.assertEqual(
            len(member_discount_code),
            0
        )
        self.assertContains(
            self.response,
            "Invalid member number"
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_INVALID_NUMBER.text,)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    def test_multiple_invalid_member_numbers(
        self,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'member_number_2': '45678',
                'g-recaptcha-response': '1234567',
            },
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(
            self.response,
            "Invalid member numbers 1234, 45678"
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    def test_multiple_valid_numbers_tickets_discounts(
        self,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'member_number_2': '4567',
                'g-recaptcha-response': '1234567',
            },
        )
        discount_code = DiscountCode.objects.filter(
            discount=discount
        )
        members_discount_code = MemberDiscountCode.objects.filter(
            discount_code=discount_code
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(
            len(members_discount_code),
            2
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    def test_duplicate_member_numbers(
        self,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'member_number_2': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        self.assertContains(
            self.response,
            'Verify repetead member number'
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE)
    def test_get_discount_for_used_member_number(
        self,
        mock_check_discount_code_in_eb,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        discount_code = DiscountCodeFactory(
            discount=discount
        )
        member_discount_code = MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        self.assertContains(
            self.response,
            'Number 1234 has already used the discount for this event'
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE)
    def test_get_discount_for_used_member_number_in_db(
        self,
        mock_check_discount_code_in_eb,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        discount_code = DiscountCodeFactory(
            discount=discount
        )
        MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.used_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        self.assertContains(
            self.response,
            'Number 1234 has already used the discount for this event'
        )


    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_MULTIPLE_USAGES)
    def test_get_discount_for_unused_discount_multiple_uses(
        self,
        mock_check_discount_code_in_eb,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        discount_code = DiscountCodeFactory(
            discount=discount
        )
        member_discount_code = MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        member_discount_code_2 = MemberDiscountCodeFactory(
            member_number=4567,
            discount_code = discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        canceled_discount = MemberDiscountCode.objects.filter(
            id=member_discount_code.id
        )
        self.assertEqual(
            canceled_discount[0].status.id,
            self.canceled_status.id
        )
        self.assertEqual(
            member_discount_code_2.status.id,
            self.unknown_status.id
        )


    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_MULTIPLE_USAGES_ONE_USED)
    @patch('bundesliga_app.views.update_discount_code_to_eb', return_value=MOCK_UPDATE_DISCOUNT_CODE_TO_EB)
    def test_get_discount_for_one_used_discount_multiple_uses(
        self,
        mock_update_discount_code_to_eb,
        mock_check_discount_code_in_eb,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        discount_code = DiscountCodeFactory(
            discount=discount
        )
        member_discount_code = MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        member_discount_code_2 = MemberDiscountCodeFactory(
            member_number=4567,
            discount_code=discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        canceled_discount = MemberDiscountCode.objects.filter(
            id=member_discount_code.id
        )
        used_discount_code = MemberDiscountCode.objects.filter(
            id=member_discount_code_2.id
        )
        self.assertEqual(
            canceled_discount[0].status.id,
            self.canceled_status.id
        )
        self.assertEqual(
            used_discount_code[0].status.id,
            self.used_status.id
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_MULTIPLE_USAGES_ONE_USED)
    @patch('bundesliga_app.views.update_discount_code_to_eb', return_value=MOCK_UPDATE_DISCOUNT_CODE_TO_EB_USES_LEFT)
    def test_get_discount_multiple_uses_with_uses_left(
        self,
        mock_update_discount_code_to_eb,
        mock_check_discount_code_in_eb,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        discount_code = DiscountCodeFactory(
            discount=discount
        )
        member_discount_code = MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        member_discount_code_2 = MemberDiscountCodeFactory(
            member_number=4567,
            discount_code=discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        canceled_discount = MemberDiscountCode.objects.filter(
            id=member_discount_code.id
        )
        used_discount_code = MemberDiscountCode.objects.filter(
            id=member_discount_code_2.id
        )
        self.assertEqual(
            canceled_discount[0].status.id,
            self.canceled_status.id
        )
        self.assertEqual(
            used_discount_code[0].status.id,
            self.used_status.id
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_ONE_USE_NOT_USED)
    def test_get_discount_not_used(
        self,
        mock_check_discount_code_in_eb,
        mock_post_ticket_discount_code_to_eb,
        mock_get_event_tickets_eb_api,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

            ticket_type = EventTicketTypeFactory(
                event=self.event,
                ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
            )
            discount = TicketTypeDiscountFactory(
                ticket_type=ticket_type
            )
            discount_code = DiscountCodeFactory(
                discount=discount
            )
            MemberDiscountCodeFactory(
                member_number=1234,
                discount_code=discount_code,
                status=self.unknown_status
            )
            self.response = self.client.get(
                '/landing_page/{}/event/{}/'.format(
                    self.organizer.id, self.event.id)
            )
            self.response = self.client.post(
                '/landing_page/{}/event/{}/'.format(
                    self.organizer.id, self.event.id),
                {
                    'tickets_type': ticket_type.id,
                    'member_number_1': '1234',
                    'g-recaptcha-response': '1234567',
                },
            )
            member_discount_codes = MemberDiscountCode.objects.all()
            self.assertEqual(
                len(member_discount_codes),
                1
            )

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value='Invalid Request',
    )
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.utils.get_event_tickets_eb_api', return_value=get_mock_event_tickets_api_paid())
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_ONE_USE_NOT_USED)
    def test_invalid_request(
            self,
            mock_check_discount_code_in_eb,
            mock_post_ticket_discount_code_to_eb,
            mock_get_event_tickets_eb_api,
            mock_get_event_eb_api,
            mock_validate_member_number_ds,
            mock_get_venue_eb_api
        ):
        ticket_type = EventTicketTypeFactory(
            event=self.event,
            ticket_id_eb=mock_get_event_tickets_eb_api.return_value[1]['id']
        )
        discount = TicketTypeDiscountFactory(
            ticket_type=ticket_type
        )
        discount_code = DiscountCodeFactory(
            discount=discount
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'tickets_type': ticket_type.id,
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        self.assertContains(self.response, "Invalid request")

    @patch(
        'bundesliga_app.forms.validate_member_number_ds',
        return_value=MOCK_DS_API_VALID_NUMBER.text,
    )
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.post_event_discount_code_to_eb', return_value={})
    def test_valid_member_number_event_discount(
            self,
            mock_post_event_discount_code_to_eb,
            mock_get_event_eb_api,
            mock_validate_member_number_ds,
            mock_get_venue_eb_api):

        EventDiscountFactory(
            event=self.event,
            value=100.0,
            value_type="percentage",
        )

        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567'
            },
        )

        self.assertEqual(self.response.status_code, 200)
        member_discount_code = MemberDiscountCode.objects.filter(
            member_number='1234'
        )
        self.assertEqual(
            len(member_discount_code),
            1
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.post_event_discount_code_to_eb', return_value={})
    def test_multiple_valid_numbers_event_discount(
        self,
        mock_post_event_discount_code_to_eb,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        discount = EventDiscountFactory(
            event=self.event,
            value=100.0,
            value_type="percentage",
        )

        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'member_number_1': '1234',
                'member_number_2': '4567',
                'g-recaptcha-response': '1234567',
            },
        )
        discount_code = DiscountCode.objects.filter(
            discount=discount
        )
        members_discount_code = MemberDiscountCode.objects.filter(
            discount_code=discount_code
        )
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(
            len(members_discount_code),
            2
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.post_event_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_ONE_USE_NOT_USED)
    def test_get_discount_not_used_event_discount(
        self,
        mock_check_discount_code_in_eb,
        mock_post_event_discount_code_to_eb,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

            discount = EventDiscountFactory(
                event=self.event,
                value=100.0,
                value_type="percentage",
            )

            discount_code = DiscountCodeFactory(
                discount=discount
            )
            MemberDiscountCodeFactory(
                member_number=1234,
                discount_code=discount_code,
                status=self.unknown_status
            )
            self.response = self.client.get(
                '/landing_page/{}/event/{}/'.format(
                    self.organizer.id, self.event.id)
            )
            self.response = self.client.post(
                '/landing_page/{}/event/{}/'.format(
                    self.organizer.id, self.event.id),
                {
                    'member_number_1': '1234',
                    'g-recaptcha-response': '1234567',
                },
            )
            member_discount_codes = MemberDiscountCode.objects.all()
            self.assertEqual(
                len(member_discount_codes),
                1
            )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.post_event_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE)
    def test_get_discount_for_used_member_number_event_discount(
        self,
        mock_check_discount_code_in_eb,
        mock_post_event_discount_code_to_eb,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        discount = EventDiscountFactory(
                event=self.event,
                value=100.0,
                value_type="percentage",
        )

        discount_code = DiscountCodeFactory(
            discount=discount
        )

        MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        self.assertContains(
            self.response,
            'Number 1234 has already used the discount for this event'
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.post_ticket_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE)
    def test_get_discount_for_used_member_number_in_db_event_discount(
        self,
        mock_check_discount_code_in_eb,
        mock_post_event_discount_code_to_eb,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        discount = EventDiscountFactory(
                event=self.event,
                value=100.0,
                value_type="percentage",
        )

        discount_code = DiscountCodeFactory(
            discount=discount
        )

        MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        self.assertContains(
            self.response,
            'Number 1234 has already used the discount for this event'
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.post_event_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_MULTIPLE_USAGES)
    def test_get_discount_for_unused_discount_multiple_uses_event_discount(
        self,
        mock_check_discount_code_in_eb,
        mock_post_event_discount_code_to_eb,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        discount = EventDiscountFactory(
                event=self.event,
                value=100.0,
                value_type="percentage",
        )

        discount_code = DiscountCodeFactory(
            discount=discount
        )

        member_discount_code = MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        member_discount_code_2 = MemberDiscountCodeFactory(
            member_number=4567,
            discount_code=discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        canceled_discount = MemberDiscountCode.objects.filter(
            id=member_discount_code.id
        )
        self.assertEqual(
            canceled_discount[0].status.id,
            self.canceled_status.id
        )
        self.assertEqual(
            member_discount_code_2.status.id,
            self.unknown_status.id
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.post_event_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_MULTIPLE_USAGES_ONE_USED)
    @patch('bundesliga_app.views.update_discount_code_to_eb', return_value=MOCK_UPDATE_DISCOUNT_CODE_TO_EB)
    def test_get_discount_for_one_used_discount_multiple_uses_event_discount(
        self,
        mock_update_discount_code_to_eb,
        mock_check_discount_code_in_eb,
        mock_post_event_discount_code_to_eb,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        discount = EventDiscountFactory(
                event=self.event,
                value=100.0,
                value_type="percentage",
        )

        discount_code = DiscountCodeFactory(
            discount=discount
        )
        member_discount_code = MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        member_discount_code_2 = MemberDiscountCodeFactory(
            member_number=4567,
            discount_code=discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        canceled_discount = MemberDiscountCode.objects.filter(
            id=member_discount_code.id
        )
        used_discount_code = MemberDiscountCode.objects.filter(
            id=member_discount_code_2.id
        )
        self.assertEqual(
            canceled_discount[0].status.id,
            self.canceled_status.id
        )
        self.assertEqual(
            used_discount_code[0].status.id,
            self.used_status.id
        )

    @patch('bundesliga_app.forms.validate_member_number_ds', return_value=MOCK_DS_API_VALID_NUMBER.text)
    @patch('bundesliga_app.views.get_event_eb_api', side_effect=get_mock_events_api)
    @patch('bundesliga_app.views.post_event_discount_code_to_eb', return_value={})
    @patch('bundesliga_app.views.check_discount_code_in_eb', return_value=MOCK_DISCOUNT_EXISTS_IN_EB_MULTIPLE_USAGES_ONE_USED)
    @patch('bundesliga_app.views.update_discount_code_to_eb', return_value=MOCK_UPDATE_DISCOUNT_CODE_TO_EB_USES_LEFT)
    def test_get_discount_multiple_uses_with_uses_left_event_discount(
        self,
        mock_update_discount_code_to_eb,
        mock_check_discount_code_in_eb,
        mock_post_event_discount_code_to_eb,
        mock_get_event_eb_api,
        mock_validate_member_number_ds,
        mock_get_venue_eb_api):

        discount = EventDiscountFactory(
                event=self.event,
                value=100.0,
                value_type="percentage",
        )

        discount_code = DiscountCodeFactory(
            discount=discount
        )
        member_discount_code = MemberDiscountCodeFactory(
            member_number=1234,
            discount_code=discount_code,
            status=self.unknown_status
        )
        member_discount_code_2 = MemberDiscountCodeFactory(
            member_number=4567,
            discount_code=discount_code,
            status=self.unknown_status
        )
        self.response = self.client.get(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id)
        )
        self.response = self.client.post(
            '/landing_page/{}/event/{}/'.format(
                self.organizer.id, self.event.id),
            {
                'member_number_1': '1234',
                'g-recaptcha-response': '1234567',
            },
        )
        canceled_discount = MemberDiscountCode.objects.filter(
            id=member_discount_code.id
        )
        used_discount_code = MemberDiscountCode.objects.filter(
            id=member_discount_code_2.id
        )
        self.assertEqual(
            canceled_discount[0].status.id,
            self.canceled_status.id
        )
        self.assertEqual(
            used_discount_code[0].status.id,
            self.used_status.id
        )


class ActivateLanguageViewTest(TestBase):
    def setUp(self):
        super(ActivateLanguageViewTest, self).setUp()

    def test_language_english(self):
        self.response = self.client.get('/language/activate/en/', **{'HTTP_REFERER':'/'})
        self.page = self.client.get(self.response.url)
        self.assertContains(
            self.page,
            "Want to manage",
        )

    def test_language_german(self):
        self.response = self.client.get('/language/activate/de/', **{'HTTP_REFERER':'/'})
        self.page = self.client.get(self.response.url)
        self.assertContains(
            self.page,
            "Möchten Sie die ",
        )

    def test_language_spanish(self):
        self.response = self.client.get('/language/activate/es/', **{'HTTP_REFERER':'/'})
        self.page = self.client.get(self.response.url)
        self.assertContains(
            self.page,
            "administrar los descuentos",
        )
