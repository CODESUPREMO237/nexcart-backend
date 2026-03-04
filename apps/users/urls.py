# Location: apps\users\urls.py
"""
NexCart User URLs
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    GoogleAuthView,
    DiscordAuthView,
    MicrosoftAuthView,
    UserProfileView,
    ChangePasswordView,
    UserListView,
    AdminUserDetailView,
    StoreSettingsView,
    ForgotPasswordView,
    ResetPasswordView,
)

app_name = 'users'

urlpatterns = [
    # Authentication
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/google/', GoogleAuthView.as_view(), name='google-auth'),
    path('auth/discord/', DiscordAuthView.as_view(), name='discord-auth'),
    path('auth/microsoft/', MicrosoftAuthView.as_view(), name='microsoft-auth'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Profile
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),

    # Password Reset
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    # Administrative
    path('admin/users/', UserListView.as_view(), name='admin-user-list'),
    path('admin/users/<uuid:id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/settings/', StoreSettingsView.as_view(), name='admin-settings'),
]
