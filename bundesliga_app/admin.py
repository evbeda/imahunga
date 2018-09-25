from django.contrib import admin
from . import models


class MemberTypeAdmin(admin.ModelAdmin):
    list_display = ("type_number", "type_name")


class DiscountAdmin(admin.ModelAdmin):
    list_display = ("discount_name",)


admin.site.register(models.MemberType, MemberTypeAdmin)
admin.site.register(models.Discount, DiscountAdmin)
