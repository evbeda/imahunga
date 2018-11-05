from django.contrib.auth import get_user_model
from django.template.defaultfilters import slugify
from social_django.models import UserSocialAuth
from factory import (
    DjangoModelFactory,
    Faker,
    Sequence,
    SubFactory,
    LazyFunction,
    lazy_attribute,
    fuzzy,
    Iterator,
)
from . import models


class OrganizerFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ('username',)

    first_name = Sequence(lambda n: "Organizer%03d" % n)
    last_name = Sequence(lambda n: "Organizer%03d" % n)
    username = lazy_attribute(
        lambda o: slugify(
            o.first_name + '.' + o.last_name,
        )
    )
    email = 'organizer@organizer.com'
    password = '12345'
    is_active = True
    is_staff = True
    is_superuser = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)


class AuthFactory(DjangoModelFactory):
    class Meta:
        model = UserSocialAuth

    user = SubFactory(OrganizerFactory)
    provider = 'eventbrite'
    uid = '234234'


class EventFactory(DjangoModelFactory):
    class Meta:
        model = models.Event

    event_id = Sequence(lambda n: n)  # 0,1,2,3 ...
    organizer = SubFactory(OrganizerFactory)
    is_active = Faker('boolean')


class EventTicketTypeFactory(DjangoModelFactory):
    class Meta:
        model = models.EventTicketType

    ticket_id_eb = Sequence(lambda n: n)  # 0,1,2,3 ...
    event = SubFactory(EventFactory)


class DiscountTypeFactory(DjangoModelFactory):
    class Meta:
        model = models.DiscountType

    name = Sequence(lambda n: n)


class DiscountFactory(DjangoModelFactory):
    class Meta:
        model = models.Discount

    name = Sequence(lambda n: u'Discount %d' % n)  # Discount0, Discount1 ...
    ticket_type = SubFactory(EventTicketTypeFactory)
    event = SubFactory(EventFactory)
    discount_type = SubFactory(DiscountTypeFactory)
    value = fuzzy.FuzzyFloat(low=0.0)  # Min value 0.0
    value_type = Iterator(["fixed", "percentage"])


class DiscountCodeFactory(DjangoModelFactory):
    class Meta:
        model = models.DiscountCode

    discount_code = Sequence(lambda n: u'code %d' % n)
    discount = SubFactory(DiscountFactory)


class StatusMemberDiscountCodeFactory(DjangoModelFactory):
    class Meta:
        model = models.StatusMemberDiscountCode

    name = Sequence(lambda n: u'Status %d' % n)


class MemberDiscountCodeFactory(DjangoModelFactory):
    class Meta:
        model = models.MemberDiscountCode

    member_number = Sequence(lambda n: n)
    status = SubFactory(StatusMemberDiscountCodeFactory)
    discount_code = SubFactory(DiscountCodeFactory)
