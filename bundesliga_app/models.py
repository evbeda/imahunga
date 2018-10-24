from django.conf import settings
from django.db import models

# Create your models here.


class Event(models.Model):
    event_id = models.CharField(max_length=200)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(default=True)


class Discount(models.Model):
    name = models.CharField(max_length=200)
    event = models.ForeignKey(Event)
    value = models.IntegerField()
    value_type = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class DiscountCode(models.Model):
    member_number = models.CharField(max_length=200)
    event = models.ForeignKey(Event)
    eb_event_id = models.CharField(max_length=200)
    discount_code = models.CharField(max_length=500)
