"""
NexCart Coupon Admin
"""
from django.contrib import admin
from .models import Coupon, CouponUsage


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'used_count',
                    'max_uses', 'valid_from', 'valid_until', 'is_active']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code', 'description']


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'user', 'discount_amount', 'used_at']
    list_filter = ['coupon']
    search_fields = ['user__email', 'coupon__code']
