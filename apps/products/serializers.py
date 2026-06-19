# Location: apps\products\serializers.py
"""
NexCart Product Serializers
"""
from rest_framework import serializers
from django.db.models import Count
from .models import Category, Product, ProductImage, ProductReview, Wishlist


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    # This maps directly to the annotated field in our View
    product_count = serializers.IntegerField(source='products_count_annotated', read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'parent', 'children', 'is_active', 'product_count']
    
    def get_image(self, obj):
        """Return full URL for category image"""
        if obj.image and obj.image.name:
            if str(obj.image.name).startswith('http'):
                return obj.image.name
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.image.url)
                return obj.image.url
            except Exception:
                return None
        return None
    
    def get_children(self, obj):
        if obj.children.exists():
            # Apply the same annotation logic to children for nested counts
            children_qs = obj.children.filter(is_active=True).annotate(
                products_count_annotated=Count('products', distinct=True)
            ).order_by('name')
            return CategorySerializer(children_qs, many=True, context=self.context).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer"""
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'position']
    
    def get_image(self, obj):
        """Return full URL for image"""
        if obj.image and obj.image.name:
            if str(obj.image.name).startswith('http'):
                return obj.image.name
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.image.url)
                return obj.image.url
            except Exception:
                return None
        return None


class ProductReviewSerializer(serializers.ModelSerializer):
    """Product review serializer"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'user', 'user_name', 'user_email',
            'rating', 'title', 'comment', 'is_verified_purchase',
            'is_approved', 'helpful_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'is_verified_purchase', 'is_approved', 'helpful_count', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Product list serializer (minimal fields)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    featured_image = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source='vendor.store_name', read_only=True, default=None)
    vendor_id = serializers.UUIDField(source='vendor.id', read_only=True, default=None)
    vendor_slug = serializers.CharField(source='vendor.slug', read_only=True, default=None)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'short_description', 'category', 'category_name',
            'price', 'compare_price', 'discount_percentage', 'featured_image',
            'is_in_stock', 'average_rating', 'review_count', 'is_featured',
            'vendor_name', 'vendor_id', 'vendor_slug'
        ]
    
    def get_featured_image(self, obj):
        """Return full URL for featured image"""
        if obj.featured_image and obj.featured_image.name:
            if str(obj.featured_image.name).startswith('http'):
                return obj.featured_image.name
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.featured_image.url)
                return obj.featured_image.url
            except Exception as e:
                print(f"Error getting image URL for {obj.name}: {e}")
                return None
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product detail serializer (full fields)"""
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()
    featured_image = serializers.SerializerMethodField()
    vendor = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'short_description',
            'category', 'tags', 'tags_list', 'price', 'compare_price',
            'discount_percentage', 'sku', 'stock_quantity', 'track_inventory',
            'allow_backorder', 'featured_image', 'images', 'meta_title',
            'meta_description', 'is_active', 'is_featured', 'is_in_stock',
            'view_count', 'purchase_count', 'average_rating', 'review_count',
            'reviews', 'vendor', 'created_at', 'updated_at'
        ]
    
    def get_featured_image(self, obj):
        """Return full URL for featured image"""
        if obj.featured_image and obj.featured_image.name:
            if str(obj.featured_image.name).startswith('http'):
                return obj.featured_image.name
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.featured_image.url)
                return obj.featured_image.url
            except Exception as e:
                print(f"Error getting image URL for {obj.name}: {e}")
                return None
        return None
    
    def get_tags_list(self, obj):
        if obj.tags:
            return [tag.strip() for tag in obj.tags.split(',')]
        return []
        
    def get_vendor(self, obj):
        if obj.vendor:
            return {
                'id': str(obj.vendor.id),
                'user_id': str(obj.vendor.user_id),
                'store_name': obj.vendor.store_name,
                'slug': obj.vendor.slug,
                'city': obj.vendor.city
            }
        return None
    
    def get_reviews(self, obj):
        reviews = obj.reviews.filter(is_approved=True).order_by('-created_at')[:5]
        return ProductReviewSerializer(reviews, many=True).data


class WishlistSerializer(serializers.ModelSerializer):
    """Wishlist serializer"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id', 'created_at']
        read_only_fields = ['id', 'created_at']