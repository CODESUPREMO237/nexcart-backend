"""
NexCart Delivery URLs
"""
from django.urls import path
from .views import DeliveryZoneListView, estimate_delivery

app_name = 'delivery'

urlpatterns = [
    path('delivery/zones/', DeliveryZoneListView.as_view(), name='delivery-zones'),
    path('delivery/estimate/', estimate_delivery, name='delivery-estimate'),
]
