"""
NexCart Price Tracking Views
Price history and price alert endpoints
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import serializers as drf_serializers

from .price_models import PriceHistory, PriceAlert
from .models import Product


class PriceHistorySerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ['id', 'price', 'recorded_at']


class PriceAlertSerializer(drf_serializers.ModelSerializer):
    product_name = drf_serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PriceAlert
        fields = ['id', 'product', 'product_name', 'target_price',
                  'is_triggered', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_triggered', 'created_at']


@api_view(['GET'])
@permission_classes([AllowAny])
def price_history(request, product_id):
    """Get price history for a product"""
    try:
        history = PriceHistory.objects.filter(product_id=product_id).order_by('recorded_at')[:90]
        serializer = PriceHistorySerializer(history, many=True)

        # Also include current price
        product = Product.objects.get(id=product_id)
        return Response({
            'current_price': float(product.price),
            'history': serializer.data
        })
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_price_alert(request):
    """Create a price drop alert"""
    try:
        product_id = request.data.get('product_id')
        target_price = request.data.get('target_price')

        if not product_id or not target_price:
            return Response({'error': 'product_id and target_price required'},
                          status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.get(id=product_id, is_active=True)

        alert, created = PriceAlert.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={
                'target_price': target_price,
                'is_active': True,
                'is_triggered': False
            }
        )

        return Response({
            'message': 'Price alert set' if created else 'Price alert updated',
            'alert': PriceAlertSerializer(alert).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_price_alerts(request):
    """List user's price alerts"""
    alerts = PriceAlert.objects.filter(user=request.user, is_active=True).select_related('product')
    return Response({
        'results': PriceAlertSerializer(alerts, many=True).data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_price_alert(request, alert_id):
    """Delete a price alert"""
    try:
        alert = PriceAlert.objects.get(id=alert_id, user=request.user)
        alert.delete()
        return Response({'message': 'Price alert deleted'}, status=status.HTTP_204_NO_CONTENT)
    except PriceAlert.DoesNotExist:
        return Response({'error': 'Alert not found'}, status=status.HTTP_404_NOT_FOUND)
