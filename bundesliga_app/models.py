from django.conf import settings
from django.db import models

# Create your models here.


class Event(models.Model):
    event_id = models.CharField(max_length=200, primary_key=True)
    name = models.CharField(max_length=200)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.name


class MemberType(models.Model):
    type_number = models.IntegerField()
    type_name = models.CharField(max_length=200)

    class Meta:
        ordering=['type_number']

    def __str__(self):
        return self.type_name


class Discount(models.Model):
    discount_name = models.CharField(max_length=200)
    event = models.ForeignKey(Event)
    membertype = models.ForeignKey(MemberType)
    discount_value = models.FloatField()
    discount_value_type = models.CharField(max_length=200)

    def __str__(self):
        return self.discount_name
