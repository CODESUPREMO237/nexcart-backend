# Location: apps\orders\views.py
"""
NexCart Order Views
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from decimal import Decimal

from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer
)
from apps.products.models import Product
from apps.products.services import ProductService


class CartView(generics.RetrieveAPIView):
    """Get user cart - requires authentication"""
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    """Add product to cart - requires authentication"""
    try:
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get product
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check stock
        if not ProductService.check_stock_availability(product_id, quantity):
            return Response({'error': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'price': product.price, 'quantity': quantity}
        )
        
        if not created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            cart_item.save()
        
        return Response(CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    try:
        quantity = int(request.data.get('quantity', 1))
        
        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1'}, status=status.HTTP_400_BAD_REQUEST)
        
        cart = Cart.objects.get(user=request.user)
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
        
        # Check stock
        if not ProductService.check_stock_availability(cart_item.product.id, quantity):
            return Response({'error': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return Response(CartItemSerializer(cart_item).data)
        
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
        cart_item.delete()
        
        return Response({'message': 'Item removed from cart'}, status=status.HTTP_204_NO_CONTENT)
        
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def cart_item_operations(request, item_id):
    """Update or delete cart item"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
        
        if request.method == 'PATCH':
            # Update quantity
            quantity = int(request.data.get('quantity', 1))
            
            if quantity < 1:
                return Response({'error': 'Quantity must be at least 1'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check stock
            if not ProductService.check_stock_availability(cart_item.product.id, quantity):
                return Response({'error': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)
            
            cart_item.quantity = quantity
            cart_item.save()
            
            return Response(CartItemSerializer(cart_item).data)
        
        elif request.method == 'DELETE':
            # Delete item
            cart_item.delete()
            return Response({'message': 'Item removed from cart'}, status=status.HTTP_204_NO_CONTENT)
            
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_cart(request):
    """Clear user cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart.items.all().delete()
        
        return Response({'message': 'Cart cleared'}, status=status.HTTP_204_NO_CONTENT)
        
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)


class OrderListView(generics.ListAPIView):
    """List user orders"""
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class OrderDetailView(generics.RetrieveAPIView):
    """Get order details"""
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderCreateView(generics.CreateAPIView):
    """Create new order from cart"""
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            # Get user cart
            cart = Cart.objects.get(user=request.user)
            
            if not cart.items.exists():
                return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate stock for all items
            for item in cart.items.all():
                if not ProductService.check_stock_availability(item.product.id, item.quantity):
                    return Response({
                        'error': f'Insufficient stock for {item.product.name}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate totals (XAF / FCFA)
            subtotal = cart.subtotal
            shipping_cost = Decimal('0') if subtotal >= Decimal('25000') else Decimal('2')  # TODO: change back to 2000 after testing
            tax = Decimal('0')  # No VAT display for local market
            total = subtotal + shipping_cost + tax
            
            # Create order
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            order = Order.objects.create(
                user=request.user,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                tax=tax,
                total=total,
                **serializer.validated_data
            )
            
            # Create order items
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_sku=item.product.sku,
                    product_image=item.product.featured_image.url if item.product.featured_image else '',
                    quantity=item.quantity,
                    price=item.price,
                    total=item.total_price
                )
                
                # Reduce stock
                ProductService.reduce_stock(item.product.id, item.quantity)
                
                # Increment purchase count
                ProductService.increment_purchase_count(item.product.id, item.quantity)
            
            # Create initial status history
            OrderStatusHistory.objects.create(
                order=order,
                status='pending',
                notes='Order created',
                created_by=request.user
            )
            
            # Clear cart
            cart.items.all().delete()
            
            return Response(
                OrderDetailSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
            
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
