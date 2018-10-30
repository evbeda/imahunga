from django.contrib import admin
from . import models


class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name",)


admin.site.register(models.Discount, DiscountAdmin)
