# Location: core\config\settings\dev.py
"""
NexCart Development Settings
"""
from .base import *

DEBUG = True

# Allow access from local network for mobile testing
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '192.168.228.100', '*']

# Database configuration is handled in base.py
# It will use DATABASE_URL from .env if available, otherwise SQLite

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Email backend - Use real SMTP so password reset emails are actually delivered
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Disable HTTPS redirect in development
SECURE_SSL_REDIRECT = False

# ==================== CLOUDINARY STORAGE ====================
# Keep using Cloudinary even in development
# This ensures consistent behavior between dev and production
# Images will be uploaded to Cloudinary, not stored locally

# Cloudinary settings are inherited from base.py
# DEFAULT_FILE_STORAGE is already set to 'cloudinary_storage.storage.MediaCloudinaryStorage'

# If you want to test with local storage during development, uncomment:
# DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
# But this is NOT recommended as it creates inconsistency with production
# ============================================================

# ==================== REDIS FIX ====================
# Use in-memory cache instead of Redis in development
# This prevents connection errors when Redis is not running
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'nexcart-dev-cache',
    }
}

# Session configuration is inherited from base.py
# No need to override here since base.py already uses db sessions

# Disable throttling in development to avoid Redis dependency
# You can re-enable with in-memory cache if needed
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # Inherit from base settings
    'DEFAULT_THROTTLE_CLASSES': [],  # Disable throttling
    # Alternatively, keep throttling with in-memory cache:
    # 'DEFAULT_THROTTLE_CLASSES': [
    #     'rest_framework.throttling.AnonRateThrottle',
    #     'rest_framework.throttling.UserRateThrottle',
    # ],
}
# ===================================================

# Django Debug Toolbar
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
