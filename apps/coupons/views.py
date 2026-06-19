"""
NexCart Coupon Views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Coupon, CouponUsage
from .serializers import CouponSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_coupon(request):
    """Validate a coupon code and return discount info"""
    try:
        code = request.data.get('code', '').strip().upper()
        order_total = float(request.data.get('order_total', 0))

        if not code:
            return Response({'error': 'Coupon code is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            return Response({'error': 'Invalid coupon code'}, status=status.HTTP_404_NOT_FOUND)

        if not coupon.is_valid:
            return Response({'error': 'This coupon has expired or is no longer valid'},
                          status=status.HTTP_400_BAD_REQUEST)

        if order_total < float(coupon.min_order_amount):
            return Response({
                'error': f'Minimum order amount is {coupon.min_order_amount} FCFA'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check per-user usage
        user_usage = CouponUsage.objects.filter(
            coupon=coupon, user=request.user
        ).count()
        if user_usage >= coupon.max_uses_per_user:
            return Response({'error': 'You have already used this coupon'},
                          status=status.HTTP_400_BAD_REQUEST)

        from decimal import Decimal
        discount = coupon.calculate_discount(Decimal(str(order_total)))

        return Response({
            'valid': True,
            'coupon': CouponSerializer(coupon).data,
            'discount_amount': float(discount),
            'new_total': float(Decimal(str(order_total)) - discount)
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
