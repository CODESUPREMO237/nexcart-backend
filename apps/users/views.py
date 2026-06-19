# Location: apps\users\views.py
"""
NexCart Authentication Views
Email/password and OAuth2 social authentication
"""
from rest_framework import status, generics,permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
import requests
import logging
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.core.cache import cache
from django.conf import settings as django_settings
from django.utils import timezone

from .models import User, UserProfile, StoreSettings, SellerKYC
from .permissions import IsAdmin
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    StoreSettingsSerializer,
    SellerKYCSerializer,
    SellerKYCAdminSerializer,
)

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """User registration with email/password"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Create user profile
            UserProfile.objects.create(user=user)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """User login with email/password"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            user = authenticate(request, email=email, password=password)
            
            if user:
                if not user.is_active:
                    return Response({
                        'error': 'Account is disabled'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                
                # Update last login
                user.save(update_fields=['last_login'])
                
                return Response({
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                })
            
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleAuthView(APIView):
    """Google OAuth2 authentication"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        token = request.data.get('token')
        
        if not token:
            return Response({
                'error': 'Token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify Google token
            google_response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {token}'}
            )
            
            if google_response.status_code != 200:
                return Response({
                    'error': 'Invalid Google token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user_info = google_response.json()
            email = user_info.get('email')
            provider_id = user_info.get('sub')
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': user_info.get('given_name', ''),
                    'last_name': user_info.get('family_name', ''),
                    'auth_provider': 'google',
                    'provider_id': provider_id,
                    'is_verified': True,
                }
            )
            
            if created:
                # Create profile
                UserProfile.objects.create(user=user)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'created': created
            })
            
        except Exception as e:
            logger.error(f"Google auth error: {str(e)}")
            return Response({
                'error': 'Authentication failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiscordAuthView(APIView):
    """Discord OAuth2 authentication"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        code = request.data.get('code')
        redirect_uri = request.data.get('redirect_uri')
        
        if not code:
            return Response({
                'error': 'Code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Exchange code for access token
            token_response = requests.post(
                'https://discord.com/api/oauth2/token',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={
                    'client_id': settings.DISCORD_CLIENT_ID,
                    'client_secret': settings.DISCORD_CLIENT_SECRET,
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri,
                }
            )
            
            token_data = token_response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                return Response({
                    'error': 'Failed to get access token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user info
            user_response = requests.get(
                'https://discord.com/api/users/@me',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            user_info = user_response.json()
            email = user_info.get('email')
            
            if not email:
                return Response({
                    'error': 'Email not available from Discord'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse username for first/last name
            username = user_info.get('username', '')
            global_name = user_info.get('global_name', username)
            name_parts = global_name.split()
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': name_parts[0] if name_parts else username,
                    'last_name': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
                    'auth_provider': 'discord',
                    'provider_id': user_info.get('id'),
                    'is_verified': user_info.get('verified', True),
                }
            )
            
            if created:
                UserProfile.objects.create(user=user)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'created': created
            })
            
        except Exception as e:
            logger.error(f"Discord auth error: {str(e)}")
            return Response({
                'error': 'Authentication failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MicrosoftAuthView(APIView):
    """Microsoft OAuth2 authentication"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        code = request.data.get('code')
        
        if not code:
            return Response({
                'error': 'Code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Exchange code for access token
            token_response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data={
                    'client_id': settings.MICROSOFT_CLIENT_ID,
                    'client_secret': settings.MICROSOFT_CLIENT_SECRET,
                    'code': code,
                    'redirect_uri': request.data.get('redirect_uri'),
                    'grant_type': 'authorization_code',
                }
            )
            
            token_data = token_response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                return Response({
                    'error': 'Failed to get access token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user info
            user_response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            user_info = user_response.json()
            email = user_info.get('mail') or user_info.get('userPrincipalName')
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': user_info.get('givenName', ''),
                    'last_name': user_info.get('surname', ''),
                    'auth_provider': 'microsoft',
                    'provider_id': user_info.get('id'),
                    'is_verified': True,
                }
            )
            
            if created:
                UserProfile.objects.create(user=user)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'created': created
            })
            
        except Exception as e:
            logger.error(f"Microsoft auth error: {str(e)}")
            return Response({
                'error': 'Authentication failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        """Override to prevent browser from caching stale role/profile data."""
        response = super().retrieve(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response

    def perform_update(self, serializer):
        """Explicitly handle nested profile updates to ensure they persist."""
        user = serializer.save()
        
        # Double-check: if profile data was in the request but didn't get saved
        # by the serializer (DRF nested writable serializer edge case), save it
        # directly here.
        profile_data = self.request.data.get('profile')
        if profile_data and isinstance(profile_data, dict):
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            changed = False
            for field, value in profile_data.items():
                if hasattr(profile, field):
                    setattr(profile, field, value)
                    changed = True
            if changed:
                profile.save()
                logger.info(f"Profile updated for user {user.email}: {profile_data}")

    def update(self, request, *args, **kwargs):
        """Override to refresh the instance from DB before serializing the response."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Refresh instance from database so response includes the latest profile data
        instance.refresh_from_db()
        # Also refresh the related profile object
        if hasattr(instance, 'profile'):
            instance.profile.refresh_from_db()

        return Response(self.get_serializer(instance).data)


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            # Check old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({
                    'error': 'Wrong password'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({'message': 'Password updated successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    """Admin-only view to list all users"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin-only view to update or delete any user"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    lookup_field = 'id'

    def perform_destroy(self, instance):
        if instance == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"error": "You cannot delete your own account"})
        instance.delete()
    
    def perform_update(self, serializer):
        if 'role' in self.request.data:
            if self.request.data['role'] == 'admin':
                serializer.save(is_staff=True, is_superuser=True)
            else:
                serializer.save(is_staff=False, is_superuser=False)
        else:
            serializer.save()


class StoreSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = StoreSettingsSerializer
    permission_classes = [IsAdmin]

    def get_object(self):
        return StoreSettings.load()


class ForgotPasswordView(APIView):
    """Send a password reset OTP to user's email"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If this email is registered, you will receive a reset code shortly.'})

        try:
            otp = get_random_string(length=6, allowed_chars='0123456789')
            cache_key = f'password_reset_otp_{email}'
            cache.set(cache_key, otp, timeout=900)

            frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_link = f"{frontend_url}/reset-password?email={email}&otp={otp}"

            send_mail(
                subject='Reset your NexCart password',
                message=(
                    f"Hi {user.first_name or 'there'},\n\n"
                    f"Your password reset code is: {otp}\n\n"
                    f"Or click the link below to reset your password:\n{reset_link}\n\n"
                    f"This code expires in 15 minutes. If you did not request this, ignore this email."
                ),
                from_email=django_settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Password reset OTP sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}")
            return Response({'error': f'Failed to send email: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'If this email is registered, you will receive a reset code shortly.'})


class ResetPasswordView(APIView):
    """Verify OTP and set a new password"""
    permission_classes = [AllowAny]

    def post(self, request):
        email       = request.data.get('email', '').strip().lower()
        otp         = request.data.get('otp', '').strip()
        new_password = request.data.get('new_password', '')

        if not all([email, otp, new_password]):
            return Response({'error': 'email, otp and new_password are required'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f'password_reset_otp_{email}'
        stored_otp = cache.get(cache_key)

        if not stored_otp or stored_otp != otp:
            return Response({'error': 'Invalid or expired reset code'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save(update_fields=['password'])
            cache.delete(cache_key)
            logger.info(f"Password reset successful for {email}")
            return Response({'message': 'Password reset successfully. You can now log in.'})
        except User.DoesNotExist:
            return Response({'error': 'Invalid or expired reset code'}, status=status.HTTP_400_BAD_REQUEST)


# ── KYC Views ────────────────────────────────────────────────────────────────

class SellerKYCSubmitView(APIView):
    """Seller submits KYC documents (id_front, id_back, selfie_with_id)"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """Return current KYC status for this seller"""
        if request.user.role != 'seller':
            return Response({'kyc': None, 'status': 'not_seller'})
        try:
            kyc = SellerKYC.objects.get(user=request.user)
            return Response(SellerKYCSerializer(kyc, context={'request': request}).data)
        except SellerKYC.DoesNotExist:
            return Response({'status': 'not_submitted'})

    def post(self, request):
        """Submit or resubmit KYC documents"""
        if request.user.role != 'seller':
            return Response(
                {'error': 'Only sellers can submit KYC.'},
                status=status.HTTP_403_FORBIDDEN
            )

        id_front = request.FILES.get('id_front')
        id_back  = request.FILES.get('id_back')
        selfie   = request.FILES.get('selfie_with_id')

        if not all([id_front, id_back, selfie]):
            return Response(
                {'error': 'id_front, id_back, and selfie_with_id are all required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update existing or create new
        try:
            kyc = SellerKYC.objects.get(user=request.user)
            # Only allow resubmission if previously rejected
            if kyc.status == 'pending':
                return Response(
                    {'error': 'Your KYC is already under review. Please wait for the admin to process it.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if kyc.status == 'approved':
                return Response(
                    {'error': 'Your KYC has already been approved.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Rejected – allow resubmission
            kyc.id_front = id_front
            kyc.id_back  = id_back
            kyc.selfie_with_id = selfie
            kyc.status = 'pending'
            kyc.rejection_reason = ''
            kyc.reviewed_at = None
            kyc.reviewed_by = None
            kyc.save()
        except SellerKYC.DoesNotExist:
            kyc = SellerKYC.objects.create(
                user=request.user,
                id_front=id_front,
                id_back=id_back,
                selfie_with_id=selfie,
            )

        return Response(
            SellerKYCSerializer(kyc, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class AdminKYCListView(generics.ListAPIView):
    """Admin: list all KYC submissions, filterable by status"""
    serializer_class = SellerKYCAdminSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = SellerKYC.objects.select_related('user', 'reviewed_by').all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class AdminKYCReviewView(APIView):
    """Admin: approve or reject a KYC submission"""
    permission_classes = [IsAdmin]

    def post(self, request, kyc_id):
        try:
            kyc = SellerKYC.objects.select_related('user').get(id=kyc_id)
        except SellerKYC.DoesNotExist:
            return Response({'error': 'KYC not found'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')  # 'approve' or 'reject'
        reason = request.data.get('reason', '').strip()

        if action not in ('approve', 'reject'):
            return Response({'error': "action must be 'approve' or 'reject'"}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'reject' and not reason:
            return Response({'error': 'A rejection reason is required.'}, status=status.HTTP_400_BAD_REQUEST)

        kyc.status = 'approved' if action == 'approve' else 'rejected'
        kyc.rejection_reason = '' if action == 'approve' else reason
        kyc.reviewed_at = timezone.now()
        kyc.reviewed_by = request.user
        kyc.save()

        # If approved, mark the vendor as verified too
        if action == 'approve':
            try:
                vendor = kyc.user.vendor_profile
                vendor.is_verified = True
                vendor.save(update_fields=['is_verified'])
            except Exception:
                pass  # no vendor profile yet – that's fine

        return Response(SellerKYCAdminSerializer(kyc, context={'request': request}).data)
