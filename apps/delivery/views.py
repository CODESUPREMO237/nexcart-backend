"""
NexCart Delivery Views
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from decimal import Decimal

from .models import DeliveryZone, DeliveryArea
from .serializers import DeliveryZoneSerializer


class DeliveryZoneListView(generics.ListAPIView):
    """List all delivery zones with areas"""
    serializer_class = DeliveryZoneSerializer
    permission_classes = [AllowAny]
    queryset = DeliveryZone.objects.filter(is_active=True).prefetch_related('areas')


@api_view(['POST'])
@permission_classes([AllowAny])
def estimate_delivery(request):
    """Estimate delivery fee and time for a given area"""
    try:
        area_id = request.data.get('area_id')
        city = request.data.get('city', '')
        order_total = Decimal(str(request.data.get('order_total', 0)))

        area = None
        zone = None

        if area_id:
            area = DeliveryArea.objects.select_related('zone').get(id=area_id, is_active=True)
            zone = area.zone
        elif city:
            area = DeliveryArea.objects.select_related('zone').filter(
                city__iexact=city, is_active=True
            ).first()
            if area:
                zone = area.zone
            else:
                # Default zone
                zone = DeliveryZone.objects.filter(is_active=True).first()

        if not zone:
            return Response({
                'delivery_fee': 2000,
                'estimated_days_min': 2,
                'estimated_days_max': 5,
                'zone_name': 'Standard',
                'message': 'Default delivery estimate'
            })

        # Calculate fee
        delivery_fee = zone.base_fee
        if area:
            delivery_fee += area.surcharge

        # Free delivery threshold
        if order_total >= zone.free_delivery_threshold:
            delivery_fee = Decimal('0')

        return Response({
            'delivery_fee': float(delivery_fee),
            'estimated_days_min': zone.estimated_days_min,
            'estimated_days_max': zone.estimated_days_max,
            'zone_name': zone.name,
            'area_name': area.name if area else None,
            'free_delivery_threshold': float(zone.free_delivery_threshold),
            'is_free_delivery': delivery_fee == 0,
        })

    except DeliveryArea.DoesNotExist:
        return Response({'error': 'Delivery area not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
