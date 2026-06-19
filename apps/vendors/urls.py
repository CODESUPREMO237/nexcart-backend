"""
NexCart Vendor URLs
"""
from django.urls import path
from .views import (
    VendorRegisterView, VendorDashboardView, VendorPublicView,
    VendorListView, VendorProductsView, VendorMyProductsView,
    VendorProductDetailView, VendorOrdersView, VendorPayoutsView,
    AdminVendorListView, approve_vendor, reject_vendor, suspend_vendor,
    contact_seller,
)

app_name = 'vendors'

urlpatterns = [
    # ── Public ───────────────────────────────────────────────────────────────
    path('vendors/', VendorListView.as_view(), name='vendor-list'),
    path('vendors/<slug:slug>/', VendorPublicView.as_view(), name='vendor-detail'),
    path('vendors/<slug:slug>/products/', VendorProductsView.as_view(), name='vendor-products'),
    path('vendors/<slug:slug>/contact/', contact_seller, name='vendor-contact'),

    # ── Seller dashboard ──────────────────────────────────────────────────────
    path('vendor/register/', VendorRegisterView.as_view(), name='vendor-register'),
    path('vendor/dashboard/', VendorDashboardView.as_view(), name='vendor-dashboard'),

    # Seller product management (pending workflow)
    path('vendor/products/', VendorMyProductsView.as_view(), name='vendor-my-products'),
    path('vendor/products/<uuid:product_id>/', VendorProductDetailView.as_view(), name='vendor-product-detail'),

    path('vendor/orders/', VendorOrdersView.as_view(), name='vendor-orders'),
    path('vendor/payouts/', VendorPayoutsView.as_view(), name='vendor-payouts'),

    # ── Admin ─────────────────────────────────────────────────────────────────
    path('admin/vendors/', AdminVendorListView.as_view(), name='admin-vendor-list'),
    path('admin/vendors/<uuid:vendor_id>/approve/', approve_vendor, name='admin-vendor-approve'),
    path('admin/vendors/<uuid:vendor_id>/reject/', reject_vendor, name='admin-vendor-reject'),
    path('admin/vendors/<uuid:vendor_id>/suspend/', suspend_vendor, name='admin-vendor-suspend'),
]
