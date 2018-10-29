# Put the mocks for tests here
from requests.models import Response
import copy


def get_mock_events_api(*args, **kwargs):
    return copy.deepcopy(MOCK_EVENT_API)


def get_mock_event_api_without_venue(*args, **kwargs):
    MOCK_EVENT_API_COPY = copy.deepcopy(MOCK_EVENT_API)
    MOCK_EVENT_API_COPY['venue_id'] = None
    return MOCK_EVENT_API_COPY


def get_mock_event_api_free(*args, **kwargs):
    MOCK_EVENT_API_COPY = copy.deepcopy(MOCK_EVENT_API)
    MOCK_EVENT_API_COPY['is_free'] = True
    return MOCK_EVENT_API_COPY


def get_mock_event_ticket(*args, **kwargs):
    ticket = {}
    ticket[MOCK_EVENT_TICKETS[0][2]['id']] = copy.deepcopy(
        MOCK_EVENT_TICKETS[0][2])
    return ticket


def get_mock_event_tickets_api_free(*args, **kwargs):
    return []


def get_mock_event_tickets_api_paid(*args, **kwargs):
    MOCK_EVENT_TICKETS_PAID = copy.deepcopy(MOCK_EVENT_TICKETS)
    # Delete free ticket from MOCK TICKETS
    del MOCK_EVENT_TICKETS_PAID[0][0]
    return MOCK_EVENT_TICKETS_PAID[0]


def get_mock_event_tickets_api_paid_inverse_position(*args, **kwargs):
    MOCK_EVENT_TICKETS_PAID = copy.deepcopy(MOCK_EVENT_TICKETS)
    # Delete free ticket from MOCK TICKETS
    del MOCK_EVENT_TICKETS_PAID[0][0]
    # new mock [ TICKET[1], TICKET[0]], so we inverse the order
    return [MOCK_EVENT_TICKETS_PAID[0][1], MOCK_EVENT_TICKETS_PAID[0][0]]

def get_mock_valid_numbers_ds(*args, **kwargs):
    MOCK_DS_VALID_NUMBERS = []
    MOCK_DS_VALID_NUMBERS.append(copy.deepcopy(MOCK_DS_API_VALID_NUMBER))
    MOCK_DS_VALID_NUMBERS.append(copy.deepcopy(MOCK_DS_API_VALID_NUMBER))
    return MOCK_DS_VALID_NUMBERS

# Deutscher Sportausweis MOCKS
# Mock for valid number


MOCK_DS_API_VALID_NUMBER = Response()
MOCK_DS_API_VALID_NUMBER.status_code = 200
MOCK_DS_API_VALID_NUMBER._content = b'{"Kartentyp": "2","Version": "00"}'

# Mock for invalid number

MOCK_DS_API_INVALID_NUMBER = Response()
MOCK_DS_API_INVALID_NUMBER.status_code = 200
MOCK_DS_API_INVALID_NUMBER._content = b'{"ERROR": -1}'

# Mock for invalid request

MOCK_DS_API_INVALID_REQUEST = Response()
MOCK_DS_API_INVALID_REQUEST.status_code = 400

# Mock get discount code doesnt exists in EB
MOCK_DISCOUNT_DOESNT_EXIST_IN_EB = {
    "discounts": [],
    "pagination": {
        "object_count": 0,
        "page_number": 1,
        "page_size": 50,
        "page_count": 1,
        "has_more_items": False
    }
}

# Mock response post discount code to EB
MOCK_POST_DISCOUNT_CODE_TO_EB = {
    "resource_uri": "https://www.eventbriteapi.com/v3/discounts/380502040/",
    "amount_off": None,
    "code": "12345",
    "discount_type": "coded",
    "end_date": "2018-01-01T10:00:00",
    "end_date_relative": None,
    "hold_ids": None,
    "id": "380502040",
    "percent_off": "15.00",
    "quantity_available": 1,
    "quantity_sold": 0,
    "start_date": "2018-01-01T10:00:00",
    "start_date_relative": None,
    "ticket_class_ids": None,
    "ticket_ids": None,
    "type": "coded",
    "event_id": "50751872216",
    "ticket_group_id": None
}

# Mock get discount code exists in EB - without usage
MOCK_DISCOUNT_EXISTS_IN_EB_NO_USAGE = {
    "discounts": [
        {
            "resource_uri": "https://www.eventbriteapi.com/v3/discounts/380379915/",
            "amount_off": None,
            "code": "5680302082",
            "discount_type": "coded",
            "end_date": "2018-01-01T10:00:00",
            "end_date_relative": None,
            "hold_ids": None,
            "id": "380379915",
            "percent_off": "15.00",
            "quantity_available": 1,
            "quantity_sold": 0,
            "start_date": "2018-01-01T10:00:00",
            "start_date_relative": None,
            "ticket_class_ids": None,
            "ticket_ids": None,
            "type": "coded",
            "event_id": "50637782972",
            "ticket_group_id": None
        }
    ],
    "pagination": {
        "object_count": 1,
        "page_number": 1,
        "page_size": 50,
        "page_count": 1,
        "has_more_items": False
    }
}

# Mock get discount code exists in EB - with usage

MOCK_DISCOUNT_EXISTS_IN_EB_WITH_USAGE = {
    "discounts": [
        {
            "resource_uri": "https://www.eventbriteapi.com/v3/discounts/380379915/",
            "amount_off": None,
            "code": "5680302082",
            "discount_type": "coded",
            "end_date": "2018-01-01T10:00:00",
            "end_date_relative": None,
            "hold_ids": None,
            "id": "380379915",
            "percent_off": "15.00",
            "quantity_available": 1,
            "quantity_sold": 1,
            "start_date": "2018-01-01T10:00:00",
            "start_date_relative": None,
            "ticket_class_ids": None,
            "ticket_ids": None,
            "type": "coded",
            "event_id": "50637782972",
            "ticket_group_id": None
        }
    ],
    "pagination": {
        "object_count": 1,
        "page_number": 1,
        "page_size": 50,
        "page_count": 1,
        "has_more_items": False
    }
}

# A random event return value of EB API '/events/:id/'

MOCK_EVENT_API = {
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
    'is_free': False,
    'version': '3.0.0',
    'logo_id': '50285339',
    'organizer_id': '17688321548',
    'venue_id': '123',
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

# A random user return value of EB API '/users/me/'
MOCK_USER_API = {
    'emails': [
        {
            'email': 'mock@mock.com',
            'verified': True,
            'primary': True
        }
    ],
    'id': '1234',
    'name': 'John Test',
    'first_name': 'John',
    'last_name': 'Test',
    'is_public': False,
    'image_id': None
}

# A random list of events return value of EB API '/users/me/owned_events/?status=live'
# In this case, the mock has the same event two times
MOCK_LIST_EVENTS_API = [
    get_mock_events_api(),
    get_mock_events_api(),
]

MOCK_VENUE_API = {
    'address': {
        'address_1': 'Test Adress',
        'address_2': None,
        'city': 'Test City',
        'region': 'Test Region',
        'postal_code': 'M5501',
        'country': 'AR',
        'latitude': '-1.0000',
        'longitude': '-1.0000',
        'localized_address_display': 'Test Adress',
        'localized_area_display': 'Test, Area',
        'localized_multi_line_address_display': [
            'Test',
            'Test, Test'
        ]
    },
    'resource_uri': 'https://test.com/',
    'id': '1',
    'age_restriction': None,
    'capacity': None,
    'name': 'Test',
    'latitude': '-1.0000',
    'longitude': '-1.0000'
}

MOCK_EVENT_TICKETS = [[
    {
        "resource_uri": "https://www.eventbriteapi.com/v3/events/50607739110/ticket_classes/94870982/",
        "variant_id": "T94870982",
        "name": "FREE",
        "description": None,
        "donation": False,
        "free": True,
        "minimum_quantity": 1,
        "maximum_quantity": None,
        "maximum_quantity_per_order": 10,
        "maximum_quantity_per_order_without_pending": 10,
        "on_sale_status": "AVAILABLE",
        "quantity_total": 10,
        "quantity_sold": 0,
        "sales_start": "2018-09-26T13:05:00Z",
        "sales_end": "2018-11-03T21:00:00Z",
        "hidden": False,
        "include_fee": False,
        "split_fee": False,
        "hide_description": True,
        "auto_hide": False,
        "variants": [],
        "has_pdf_ticket": True,
        "sales_channels": [
                "online",
                "atd"
        ],
        "short_name": "FREE",
        "delivery_methods": [
            "electronic"
        ],
        "event_id": "50607739110",
        "id": "94870982"
    },
    {
        "actual_cost": {
            "display": "$20.00",
            "currency": "ARS",
            "value": 2000,
            "major_value": "20.00"
        },
        "actual_fee": {
            "display": "$1.69",
            "currency": "ARS",
            "value": 169,
            "major_value": "1.69"
        },
        "cost": {
            "display": "$20.00",
            "currency": "ARS",
            "value": 2000,
            "major_value": "20.00"
        },
        "fee": {
            "display": "$1.69",
            "currency": "ARS",
            "value": 169,
            "major_value": "1.69"
        },
        "tax": {
            "display": "$0.00",
            "currency": "ARS",
            "value": 0,
            "major_value": "0.00"
        },
        "resource_uri": "https://www.eventbriteapi.com/v3/events/50607739110/ticket_classes/95139203/",
        "variant_id": "T95139203",
        "name": "Socio",
        "description": None,
        "donation": False,
        "free": False,
        "minimum_quantity": 1,
        "maximum_quantity": None,
        "maximum_quantity_per_order": 9,
        "maximum_quantity_per_order_without_pending": 9,
        "on_sale_status": "AVAILABLE",
        "quantity_total": 10,
        "quantity_sold": 1,
        "sales_start": "2018-10-01T08:30:00Z",
        "sales_end": "2018-11-03T21:00:00Z",
        "hidden": False,
        "include_fee": False,
        "split_fee": False,
        "hide_description": True,
        "auto_hide": False,
        "variants": [],
        "has_pdf_ticket": True,
        "sales_channels": [
                "online",
                "atd"
        ],
        "short_name": "Socio",
        "delivery_methods": [
            "electronic"
        ],
        "event_id": "50607739110",
        "id": "95139203"
    },
    {
        "actual_cost": {
            "display": "$300.00",
            "currency": "ARS",
            "value": 30000,
            "major_value": "300.00"
        },
        "actual_fee": {
            "display": "$25.37",
            "currency": "ARS",
            "value": 2537,
            "major_value": "25.37"
        },
        "cost": {
            "display": "$300.00",
            "currency": "ARS",
            "value": 30000,
            "major_value": "300.00"
        },
        "fee": {
            "display": "$25.37",
            "currency": "ARS",
            "value": 2537,
            "major_value": "25.37"
        },
        "tax": {
            "display": "$0.00",
            "currency": "ARS",
            "value": 0,
            "major_value": "0.00"
        },
        "resource_uri": "https://www.eventbriteapi.com/v3/events/50607739110/ticket_classes/95845509/",
        "variant_id": "T95845509",
        "name": "VIP",
        "description": None,
        "donation": False,
        "free": False,
        "minimum_quantity": 1,
        "maximum_quantity": None,
        "maximum_quantity_per_order": 10,
        "maximum_quantity_per_order_without_pending": 10,
        "on_sale_status": "AVAILABLE",
        "quantity_total": 10,
        "quantity_sold": 0,
        "sales_start": "2018-10-11T10:45:00Z",
        "sales_end": "2018-11-03T21:00:00Z",
        "hidden": False,
        "include_fee": False,
        "split_fee": False,
        "hide_description": True,
        "auto_hide": False,
        "variants": [],
        "has_pdf_ticket": True,
        "sales_channels": [
                "online",
                "atd"
        ],
        "short_name": "VIP",
        "delivery_methods": [
            "electronic"
        ],
        "event_id": "50607739110",
        "id": "95845509"
    }
]]
