"""
NexCart Vendor Views
"""
from rest_framework import generics, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.utils.text import slugify

from .models import Vendor, VendorPayout
from .serializers import (
    VendorSerializer, VendorRegistrationSerializer,
    VendorDashboardSerializer, VendorPayoutSerializer
)
from apps.products.models import Product, Category
from apps.products.serializers import ProductListSerializer, ProductDetailSerializer
from apps.users.permissions import IsAdmin


# ────────────────────────────────────────────────────────────────────────────
# Public vendor views
# ────────────────────────────────────────────────────────────────────────────

class VendorRegisterView(generics.CreateAPIView):
    """Register as a vendor"""
    serializer_class = VendorRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if hasattr(request.user, 'vendor_profile'):
            return Response(
                {'error': 'You are already registered as a vendor'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor = serializer.save(user=request.user)

        # NOTE: user role stays 'user' until admin approves the store

        return Response({
            'message': 'Vendor registration submitted for approval',
            'vendor': VendorDashboardSerializer(vendor, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class VendorDashboardView(generics.RetrieveUpdateAPIView):
    """Vendor dashboard - view and update store info"""
    serializer_class = VendorDashboardSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Vendor.objects.get(user=self.request.user)


class VendorPublicView(generics.RetrieveAPIView):
    """Public vendor storefront"""
    serializer_class = VendorSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    queryset = Vendor.objects.filter(is_active=True, status='approved')


class VendorListView(generics.ListAPIView):
    """List all approved vendors"""
    serializer_class = VendorSerializer
    permission_classes = [AllowAny]
    queryset = Vendor.objects.filter(is_active=True, status='approved')


class VendorProductsView(generics.ListAPIView):
    """List products for a specific vendor (public) - only approved"""
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_slug = self.kwargs.get('slug')
        return Product.objects.filter(
            vendor__slug=vendor_slug,
            vendor__is_active=True,
            is_active=True,
            approval_status='approved',
        ).select_related('category')


# ────────────────────────────────────────────────────────────────────────────
# Seller product management  (creates pending items for admin approval)
# ────────────────────────────────────────────────────────────────────────────

class VendorMyProductsView(generics.ListCreateAPIView):
    """
    Seller: list their own products (all statuses) and create new ones.
    New products go into 'pending' state until an admin approves them.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_vendor(self):
        try:
            return Vendor.objects.get(user=self.request.user)
        except Vendor.DoesNotExist:
            return None

    def get_serializer_class(self):
        return ProductListSerializer

    def get_queryset(self):
        vendor = self._get_vendor()
        if not vendor:
            return Product.objects.none()
        return Product.objects.filter(vendor=vendor).select_related('category').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = ProductListSerializer(qs, many=True, context={'request': request})
        data = serializer.data
        # Enrich with approval info
        for i, product in enumerate(qs):
            data[i]['approval_status'] = product.approval_status
            data[i]['pending_deletion'] = product.pending_deletion
        return Response({'results': data, 'count': len(data)})

    def create(self, request, *args, **kwargs):
        vendor = self._get_vendor()
        if not vendor:
            return Response({'error': 'You must be a registered vendor to add products.'}, status=status.HTTP_403_FORBIDDEN)
        if vendor.status != 'approved':
            return Response({'error': 'Your vendor account must be approved before you can add products.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        name = data.get('name', '').strip()
        if not name:
            return Response({'error': 'Product name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Build a unique slug
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        # Get category
        category_id = data.get('category')
        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return Response({'error': 'Invalid category.'}, status=status.HTTP_400_BAD_REQUEST)

        # Auto-generate SKU
        import random, string
        sku = 'VND-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while Product.objects.filter(sku=sku).exists():
            sku = 'VND-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Cast numeric fields — multipart form data sends everything as strings
        try:
            price = float(data.get('price', 0))
        except (TypeError, ValueError):
            price = 0

        compare_price_raw = data.get('compare_price')
        try:
            compare_price = float(compare_price_raw) if compare_price_raw else None
        except (TypeError, ValueError):
            compare_price = None

        try:
            stock_quantity = int(data.get('stock_quantity', 0))
        except (TypeError, ValueError):
            stock_quantity = 0

        product = Product(
            name=name,
            slug=slug,
            description=data.get('description', ''),
            short_description=data.get('short_description', data.get('description', '')[:200]),
            price=price,
            compare_price=compare_price,
            sku=sku,
            stock_quantity=stock_quantity,
            tags=data.get('tags', ''),
            category=category,
            vendor=vendor,
            is_active=False,          # not live until approved
            approval_status='pending', # requires admin approval
        )

        # Handle image upload
        if 'featured_image' in request.FILES:
            product.featured_image = request.FILES['featured_image']

        product.save()

        # Update vendor product count
        vendor.total_products = Product.objects.filter(vendor=vendor, is_active=True).count()
        vendor.save(update_fields=['total_products'])

        serializer = ProductListSerializer(product, context={'request': request})
        return Response({
            'message': 'Product submitted for admin approval. It will go live once approved.',
            'product': serializer.data,
            'approval_status': product.approval_status,
        }, status=status.HTTP_201_CREATED)


class VendorProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Seller: view, update or delete a specific product.
    Updates/deletes are queued for admin approval.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        try:
            vendor = Vendor.objects.get(user=self.request.user)
            return Product.objects.filter(vendor=vendor)
        except Vendor.DoesNotExist:
            return Product.objects.none()

    def get_object(self):
        qs = self.get_queryset()
        product_id = self.kwargs.get('product_id')
        try:
            return qs.get(id=product_id)
        except Product.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Product not found or does not belong to your store.')

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = ProductDetailSerializer(product, context={'request': request})
        data = serializer.data
        data['approval_status'] = product.approval_status
        data['pending_deletion'] = product.pending_deletion
        data['pending_update_data'] = product.pending_update_data
        return Response(data)

    def partial_update(self, request, *args, **kwargs):
        product = self.get_object()

        # Capture the proposed changes
        allowed_fields = [
            'name', 'description', 'short_description', 'price',
            'compare_price', 'stock_quantity', 'tags', 'is_featured',
            'meta_title', 'meta_description',
        ]
        pending = {}
        for field in allowed_fields:
            if field in request.data:
                pending[field] = request.data[field]

        if not pending:
            return Response({'error': 'No updatable fields provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Store changes and mark pending
        product.pending_update_data = pending
        product.approval_status = 'pending'
        product.save(update_fields=['pending_update_data', 'approval_status'])

        return Response({
            'message': 'Product update submitted for admin approval.',
            'pending_changes': pending,
            'approval_status': product.approval_status,
        })

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()

        if product.pending_deletion:
            return Response({'message': 'This product is already pending deletion.'}, status=status.HTTP_200_OK)

        # Flag for admin confirmation instead of immediate delete
        product.pending_deletion = True
        product.approval_status = 'pending'
        product.is_active = False
        product.save(update_fields=['pending_deletion', 'approval_status', 'is_active'])

        return Response({
            'message': 'Deletion request submitted. An admin will permanently remove this product.',
            'product_id': str(product.id),
        })


# ────────────────────────────────────────────────────────────────────────────
# Message Seller endpoint
# ────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def contact_seller(request, slug):
    """Send a message to a seller — creates a chat conversation"""
    try:
        vendor = Vendor.objects.get(slug=slug, is_active=True)
    except Vendor.DoesNotExist:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)

    message_text = request.data.get('message', '').strip()
    if not message_text:
        return Response({'error': 'Message cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

    # Create or reuse a chat conversation
    try:
        from apps.chat.models import Conversation, Message

        # Get product if provided
        product_id = request.data.get('product_id')
        product = None
        if product_id:
            from apps.products.models import Product
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                pass

        # Get or create conversation using buyer/seller FK fields
        conversation, created = Conversation.objects.get_or_create(
            buyer=request.user,
            seller=vendor.user,
            product=product,
            defaults={'vendor': vendor}
        )

        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=message_text
        )

        # Update last_message_at
        from django.utils import timezone
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=['last_message_at'])

        return Response({
            'message': 'Message sent to seller successfully.',
            'conversation_id': str(conversation.id),
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"contact_seller error: {e}")
        return Response({
            'error': 'Failed to send message. Please try again.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ────────────────────────────────────────────────────────────────────────────
# Vendor order and payout views
# ────────────────────────────────────────────────────────────────────────────

class VendorOrdersView(generics.ListAPIView):
    """List orders containing vendor's products"""
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        from apps.orders.models import OrderItem, Order
        from apps.orders.serializers import OrderListSerializer

        vendor = Vendor.objects.get(user=request.user)
        order_ids = OrderItem.objects.filter(
            product__vendor=vendor
        ).values_list('order_id', flat=True).distinct()

        orders = Order.objects.filter(id__in=order_ids).order_by('-created_at')
        serializer = OrderListSerializer(orders, many=True)
        return Response({'results': serializer.data, 'count': len(serializer.data)})


class VendorPayoutsView(generics.ListAPIView):
    """List vendor payouts"""
    serializer_class = VendorPayoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        vendor = Vendor.objects.get(user=self.request.user)
        return VendorPayout.objects.filter(vendor=vendor)


# ────────────────────────────────────────────────────────────────────────────
# Admin vendor management
# ────────────────────────────────────────────────────────────────────────────

class AdminVendorListView(generics.ListAPIView):
    """Admin: list all vendors"""
    serializer_class = VendorDashboardSerializer
    permission_classes = [IsAdmin]
    queryset = Vendor.objects.all()


@api_view(['POST'])
@permission_classes([IsAdmin])
def approve_vendor(request, vendor_id):
    """Admin: approve a vendor"""
    try:
        vendor = Vendor.objects.get(id=vendor_id)
        vendor.status = 'approved'
        vendor.is_active = True
        vendor.approved_at = timezone.now()
        vendor.save()
        # Promote user to seller role
        vendor.user.role = 'seller'
        vendor.user.save(update_fields=['role'])
        return Response({'message': f'Vendor {vendor.store_name} approved'})
    except Vendor.DoesNotExist:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdmin])
def reject_vendor(request, vendor_id):
    """Admin: reject a vendor"""
    try:
        vendor = Vendor.objects.get(id=vendor_id)
        vendor.status = 'rejected'
        vendor.is_active = False
        vendor.save()
        # Demote user back to regular user
        vendor.user.role = 'user'
        vendor.user.save(update_fields=['role'])
        return Response({'message': f'Vendor {vendor.store_name} rejected'})
    except Vendor.DoesNotExist:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdmin])
def suspend_vendor(request, vendor_id):
    """Admin: suspend a vendor"""
    try:
        vendor = Vendor.objects.get(id=vendor_id)
        vendor.status = 'suspended'
        vendor.is_active = False
        vendor.save()
        # Demote user back to regular user
        vendor.user.role = 'user'
        vendor.user.save(update_fields=['role'])
        return Response({'message': f'Vendor {vendor.store_name} suspended'})
    except Vendor.DoesNotExist:
        return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)

