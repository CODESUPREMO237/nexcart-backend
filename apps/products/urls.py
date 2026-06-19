"""
NexCart Products URLs
"""
from django.urls import path
from .views import (
    CategoryListView,
    ProductListView,
    ProductDetailView,
    FeaturedProductsView,
    ProductReviewListCreateView,
    WishlistView,
    WishlistAddView,
    WishlistRemoveView,
    track_activity
)
from .views_admin import (
    PendingProductListView,
    approve_product,
    reject_product,
    confirm_delete_product,
    admin_all_products,
    approve_review,
)
from .image_search import visual_search
from .price_views import price_history, create_price_alert, my_price_alerts, delete_price_alert

app_name = 'products'

urlpatterns = [
    # Categories
    path('categories/', CategoryListView.as_view(), name='category-list'),

    # Products - Featured MUST come before detail view
    path('products/featured/', FeaturedProductsView.as_view(), name='featured-products'),
    path('products/visual-search/', visual_search, name='visual-search'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<uuid:id>/', ProductDetailView.as_view(), name='product-detail'),

    # Reviews
    path('products/<uuid:product_id>/reviews/', ProductReviewListCreateView.as_view(), name='product-reviews'),
    path('reviews/', ProductReviewListCreateView.as_view(), name='review-create'),

    # Wishlist
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/add/', WishlistAddView.as_view(), name='wishlist-add'),
    path('wishlist/<uuid:id>/', WishlistRemoveView.as_view(), name='wishlist-remove'),

    # Activity tracking
    path('activity/track/', track_activity, name='track-activity'),

    # Price tracking
    path('products/<uuid:product_id>/price-history/', price_history, name='price-history'),
    path('price-alerts/', my_price_alerts, name='price-alerts'),
    path('price-alerts/create/', create_price_alert, name='price-alert-create'),
    path('price-alerts/<uuid:alert_id>/', delete_price_alert, name='price-alert-delete'),

    # ─── Admin approval endpoints ───────────────────────────────────────────
    path('admin/products/', admin_all_products, name='admin-all-products'),
    path('admin/products/pending/', PendingProductListView.as_view(), name='admin-pending-products'),
    path('admin/products/<uuid:product_id>/approve/', approve_product, name='admin-approve-product'),
    path('admin/products/<uuid:product_id>/reject/', reject_product, name='admin-reject-product'),
    path('admin/products/<uuid:product_id>/confirm-delete/', confirm_delete_product, name='admin-confirm-delete-product'),
    path('admin/reviews/<uuid:review_id>/approve/', approve_review, name='admin-approve-review'),
]
