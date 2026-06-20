# Location: core\config\views.py
"""
Core configuration views
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "HEAD"])
def api_health(request):
    """API health check endpoint"""
    return JsonResponse({
        'status': 'ok',
        'message': 'NexCart API is running',
        'version': '1.0.0'
    })


@require_http_methods(["GET"])
def api_404(request, exception=None):
    """Custom 404 JSON response for API"""
    return JsonResponse({
        'error': 'Not Found',
        'message': f'The endpoint {request.path} does not exist',
        'status': 404
    }, status=404)
