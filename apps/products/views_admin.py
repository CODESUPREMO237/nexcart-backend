"""
NexCart Admin Product Approval Views
All endpoints protected by IsAdmin permission.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.products.models import Product, ProductReview
from apps.products.serializers import ProductListSerializer, ProductDetailSerializer
from apps.users.permissions import IsAdmin


class PendingProductListView(generics.ListAPIView):
    """
    Admin: list all products that need attention
    - approval_status = 'pending' (new submissions)
    - pending_deletion = True   (deletion requests)
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return Product.objects.filter(
            approval_status='pending'
        ).select_related('category', 'vendor', 'vendor__user').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True, context={'request': request})
        data = serializer.data
        # Enrich each item with pending_type for the frontend
        for i, product in enumerate(qs):
            if product.pending_deletion:
                data[i]['pending_type'] = 'deletion'
            elif product.pending_update_data:
                data[i]['pending_type'] = 'update'
            else:
                data[i]['pending_type'] = 'new'
        return Response({'results': data, 'count': len(data)})


@api_view(['POST'])
@permission_classes([IsAdmin])
def approve_product(request, product_id):
    """Admin: approve a product (new, update, or restore from rejected)"""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    # If there is a pending update, apply it now
    if product.pending_update_data:
        update_data = product.pending_update_data
        allowed_fields = [
            'name', 'description', 'short_description', 'price',
            'compare_price', 'stock_quantity', 'tags', 'is_featured',
            'meta_title', 'meta_description',
        ]
        for field in allowed_fields:
            if field in update_data:
                setattr(product, field, update_data[field])
        product.pending_update_data = None

    product.approval_status = 'approved'
    product.is_active = True
    product.save()

    return Response({
        'message': f'Product "{product.name}" approved successfully.',
        'product_id': str(product.id),
        'approval_status': product.approval_status,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def reject_product(request, product_id):
    """Admin: reject a product submission or update"""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    reason = request.data.get('reason', '')
    product.approval_status = 'rejected'
    product.is_active = False
    # Keep pending_update_data for audit; clear it
    product.pending_update_data = None
    product.pending_deletion = False
    product.save()

    return Response({
        'message': f'Product "{product.name}" rejected.',
        'reason': reason,
        'product_id': str(product.id),
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def confirm_delete_product(request, product_id):
    """Admin: permanently delete a product that a seller requested to remove"""
    try:
        product = Product.objects.get(id=product_id, pending_deletion=True)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found or not flagged for deletion'},
            status=status.HTTP_404_NOT_FOUND
        )

    name = product.name
    product.delete()
    return Response({'message': f'Product "{name}" permanently deleted.'})


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_all_products(request):
    """Admin: list ALL products with their approval status (paginated)"""
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 20))
    status_filter = request.query_params.get('status', None)
    search = request.query_params.get('search', '')

    qs = Product.objects.select_related('category', 'vendor').order_by('-created_at')
    if status_filter:
        qs = qs.filter(approval_status=status_filter)
    if search:
        qs = qs.filter(name__icontains=search)

    total = qs.count()
    start = (page - 1) * limit
    products = qs[start:start + limit]
    serializer = ProductListSerializer(products, many=True, context={'request': request})

    return Response({
        'results': serializer.data,
        'count': total,
        'page': page,
        'total_pages': (total + limit - 1) // limit,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def approve_review(request, review_id):
    """Admin: approve a pending review"""
    try:
        review = ProductReview.objects.get(id=review_id)
    except ProductReview.DoesNotExist:
        return Response({'error': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)

    review.is_approved = True
    review.save()
    return Response({'message': 'Review approved.'})
