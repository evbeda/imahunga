from django.conf import settings
from django.db import models

# Create your models here.


class Event(models.Model):
    event_id = models.CharField(max_length=200, unique=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(default=True)


class EventTicketType(models.Model):
    event = models.ForeignKey(
        Event
    )
    ticket_id_eb = models.CharField(max_length=200, unique=True)


class DiscountType(models.Model):
    name = models.CharField(max_length=200, unique=True)


class Discount(models.Model):
    name = models.CharField(max_length=200)
    discount_type = models.ForeignKey(DiscountType)
    value = models.IntegerField()
    value_type = models.CharField(max_length=200)


class EventDiscount(Discount):
    event = models.ForeignKey(Event)


class TicketTypeDiscount(Discount):
    ticket_type = models.ForeignKey(EventTicketType)


class DiscountCode(models.Model):
    discount = models.ForeignKey(Discount)
    discount_code = models.CharField(max_length=500)


class StatusMemberDiscountCode(models.Model):
    name = models.CharField(max_length=200)


class MemberDiscountCode(models.Model):
    discount_code = models.ForeignKey(DiscountCode)
    member_number = models.CharField(max_length=200)
    status = models.ForeignKey(StatusMemberDiscountCode)
