"""
NexCart Analytics URLs
"""
from django.urls import path
from .views import dashboard_stats, sales_chart, top_products, recent_orders

app_name = 'analytics'

urlpatterns = [
    path('analytics/dashboard/', dashboard_stats, name='dashboard-stats'),
    path('analytics/sales-chart/', sales_chart, name='sales-chart'),
    path('analytics/top-products/', top_products, name='top-products'),
    path('analytics/recent-orders/', recent_orders, name='recent-orders'),
]
