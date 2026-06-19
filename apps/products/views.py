# Location: apps\products\views.py
"""
NexCart Product Views
"""
from rest_framework import generics, filters, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.db.models import Q
from django.db.models import Count # Add this import at the top

from .models import Category, Product, ProductReview, Wishlist
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductReviewSerializer,
    WishlistSerializer
)
from .filters import ProductFilter
from .services import ProductService
from apps.users.models import UserActivity

from django.db.models import Count, Q
from django.db.models.functions import Coalesce

class CategoryListView(generics.ListAPIView):
    """List all parent categories with recursive product counts"""
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        # Annotate with products in this category PLUS products in child categories
        return Category.objects.filter(is_active=True, parent=None).annotate(
            products_count_annotated=Count('products', distinct=True) + 
            Count('children__products', distinct=True)
        ).order_by('name') # Resolves the UnorderedObjectListWarning


class ProductListView(generics.ListAPIView):
    """List and filter products"""
    queryset = Product.objects.filter(is_active=True).select_related('category').order_by('-created_at')
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'tags']
    ordering_fields = ['price', 'created_at', 'average_rating', 'purchase_count']


class ProductDetailView(generics.RetrieveAPIView):
    """Get product details"""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Increment view count
        ProductService.increment_view_count(instance.id)
        
        # Track user activity
        if request.user.is_authenticated:
            UserActivity.objects.create(
                user=request.user,
                session_id=request.session.session_key or '',
                activity_type='view',
                product=instance
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class FeaturedProductsView(generics.ListAPIView):
    """Get featured products"""
    queryset = Product.objects.filter(is_active=True, is_featured=True).select_related('category')[:8]
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]


class ProductReviewListCreateView(generics.ListCreateAPIView):
    """List and create product reviews"""
    serializer_class = ProductReviewSerializer
    
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        return ProductReview.objects.filter(
            product_id=product_id,
            is_approved=True
        ).order_by('-created_at')
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def perform_create(self, serializer):
        # Support both URL kwarg (nested route) and request body field
        product_id = self.kwargs.get('product_id') or self.request.data.get('product') or self.request.data.get('product_id')
        
        if not product_id:
            raise serializers.ValidationError({'product': 'This field is required.'})
        
        # Validate rating
        rating = self.request.data.get('rating')
        if not rating or int(rating) < 1:
            raise serializers.ValidationError({'rating': 'Please select a rating.'})
        
        # Check if user has already reviewed this product
        if ProductReview.objects.filter(
            user=self.request.user,
            product_id=product_id
        ).exists():
            raise serializers.ValidationError("You have already reviewed this product")
        
        serializer.save(user=self.request.user, product_id=product_id)
        
        # Update product rating
        ProductService.update_product_rating(product_id)


class WishlistView(generics.ListAPIView):
    """Get user wishlist"""
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product')


class WishlistAddView(generics.CreateAPIView):
    """Add product to wishlist"""
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        product_id = self.request.data.get('product_id')
        
        # Check if already in wishlist
        if Wishlist.objects.filter(
            user=self.request.user,
            product_id=product_id
        ).exists():
            raise serializers.ValidationError("Product already in wishlist")
        
        serializer.save(user=self.request.user)


class WishlistRemoveView(generics.DestroyAPIView):
    """Remove product from wishlist"""
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([AllowAny])
def track_activity(request):
    """Track user activity"""
    try:
        activity_type = request.data.get('activity_type')
        product_id = request.data.get('product_id')
        metadata = request.data.get('metadata', {})
        
        UserActivity.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key or '',
            activity_type=activity_type,
            product_id=product_id,
            metadata=metadata,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'status': 'success'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)