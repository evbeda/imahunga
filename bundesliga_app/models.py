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


class Discount(models.Model):
    name = models.CharField(max_length=200)
    ticket_type = models.ForeignKey(EventTicketType)
    value = models.IntegerField()
    value_type = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class DiscountCode(models.Model):
    member_number = models.CharField(max_length=200)
    discount = models.ForeignKey(Discount)
    eb_event_id = models.CharField(max_length=200)
    discount_code = models.CharField(max_length=500)
