"""
NexCart Vendor Admin
"""
from django.contrib import admin
from .models import Vendor, VendorPayout


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'user', 'city', 'status', 'is_active', 'total_sales', 'created_at']
    list_filter = ['status', 'is_active', 'is_verified', 'city', 'region']
    search_fields = ['store_name', 'user__email', 'phone']
    readonly_fields = ['id', 'slug', 'total_sales', 'total_products', 'average_rating', 'created_at', 'updated_at']
    actions = ['approve_vendors', 'reject_vendors']

    def approve_vendors(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', is_active=True, approved_at=timezone.now())
    approve_vendors.short_description = "Approve selected vendors"

    def reject_vendors(self, request, queryset):
        queryset.update(status='rejected', is_active=False)
    reject_vendors.short_description = "Reject selected vendors"


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['vendor__store_name', 'transaction_id']
