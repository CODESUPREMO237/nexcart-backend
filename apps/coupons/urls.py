"""
NexCart Coupon URLs
"""
from django.urls import path
from .views import validate_coupon

app_name = 'coupons'

urlpatterns = [
    path('coupons/validate/', validate_coupon, name='coupon-validate'),
]
