"""
NexCart Analytics Views
Admin dashboard analytics
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta

from apps.users.permissions import IsAdmin
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.users.models import User, UserActivity
from apps.vendors.models import Vendor


@api_view(['GET'])
@permission_classes([IsAdmin])
def dashboard_stats(request):
    """Get main dashboard statistics"""
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Revenue
    total_revenue = Order.objects.filter(
        payment_status='completed'
    ).aggregate(total=Sum('total'))['total'] or 0

    monthly_revenue = Order.objects.filter(
        payment_status='completed',
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('total'))['total'] or 0

    weekly_revenue = Order.objects.filter(
        payment_status='completed',
        created_at__gte=seven_days_ago
    ).aggregate(total=Sum('total'))['total'] or 0

    # Orders
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    monthly_orders = Order.objects.filter(created_at__gte=thirty_days_ago).count()

    # Users
    total_users = User.objects.count()
    new_users_month = User.objects.filter(date_joined__gte=thirty_days_ago).count()

    # Products
    total_products = Product.objects.filter(is_active=True).count()
    low_stock = Product.objects.filter(
        is_active=True, track_inventory=True, stock_quantity__lt=5
    ).count()

    # Vendors
    total_vendors = Vendor.objects.filter(status='approved').count()
    pending_vendors = Vendor.objects.filter(status='pending').count()

    return Response({
        'revenue': {
            'total': float(total_revenue),
            'monthly': float(monthly_revenue),
            'weekly': float(weekly_revenue),
        },
        'orders': {
            'total': total_orders,
            'pending': pending_orders,
            'monthly': monthly_orders,
        },
        'users': {
            'total': total_users,
            'new_this_month': new_users_month,
        },
        'products': {
            'total': total_products,
            'low_stock': low_stock,
        },
        'vendors': {
            'total': total_vendors,
            'pending_approval': pending_vendors,
        }
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def sales_chart(request):
    """Get sales data for charts"""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    daily_sales = Order.objects.filter(
        payment_status='completed',
        created_at__gte=start_date
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        revenue=Sum('total'),
        orders=Count('id')
    ).order_by('date')

    return Response({
        'data': list(daily_sales),
        'period_days': days
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def top_products(request):
    """Get top selling products"""
    limit = int(request.GET.get('limit', 10))

    products = Product.objects.filter(
        is_active=True
    ).order_by('-purchase_count')[:limit].values(
        'id', 'name', 'price', 'purchase_count',
        'view_count', 'average_rating', 'stock_quantity'
    )

    return Response({'results': list(products)})


@api_view(['GET'])
@permission_classes([IsAdmin])
def recent_orders(request):
    """Get recent orders"""
    limit = int(request.GET.get('limit', 20))

    from apps.orders.serializers import OrderListSerializer
    orders = Order.objects.all().order_by('-created_at')[:limit]
    serializer = OrderListSerializer(orders, many=True)

    return Response({'results': serializer.data})
