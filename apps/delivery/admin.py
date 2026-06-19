"""
NexCart Delivery Admin
"""
from django.contrib import admin
from .models import DeliveryZone, DeliveryArea


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'base_fee', 'free_delivery_threshold',
                    'estimated_days_min', 'estimated_days_max', 'is_active']
    list_filter = ['region', 'is_active']
    search_fields = ['name', 'region']


@admin.register(DeliveryArea)
class DeliveryAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'zone', 'surcharge', 'is_active']
    list_filter = ['city', 'zone', 'is_active']
    search_fields = ['name', 'city']
