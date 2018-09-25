from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'createDiscount$', views.CreateDiscount.as_view(), name="createDiscount"),
]
