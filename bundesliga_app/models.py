from django.db import models

# Create your models here.


class Organizer(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)

    def __str__(self):
        return self.first_name


class Event(models.Model):
    event_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=200)
    organizer = models.ForeignKey(Organizer)

    def __str__(self):
        return self.name
