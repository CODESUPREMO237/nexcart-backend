"""
NexCart Visual Search
Image-based product search using color histogram matching
No heavy ML dependencies - uses numpy only
"""
import io
import logging
import numpy as np
import requests
from PIL import Image
from rest_framework.decorators import api_view, permission_classes, parser_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser
from rest_framework import status

from core.common.authentication import OptionalJWTAuthentication
from .models import Product
from .serializers import ProductListSerializer

logger = logging.getLogger(__name__)


def _load_image_bytes(image_file):
    """Resolve raw image bytes from either an uploaded file or a remote-storage FieldFile.

    Cloudinary's storage backend (django-cloudinary-storage) does NOT support
    opening files by name via Django's Storage API - `storage.open()` always
    raises IOError there, because Cloudinary is meant to be read via its public
    URL, not fetched through the Django filesystem abstraction. So for any
    FieldFile-like object we instead fetch the bytes over HTTP from `.url`.
    """
    # Plain uploaded file from a request (already in-memory / readable).
    if not hasattr(image_file, 'url'):
        if hasattr(image_file, 'seek'):
            try:
                image_file.seek(0)
            except Exception:
                pass
        return image_file.read()

    # FieldFile backed by remote storage (Cloudinary, S3, etc.) - fetch via URL.
    #
    # NOTE: in this project, `.name` is sometimes already a full absolute URL
    # (e.g. seed/fixture data stored the whole Cloudinary URL directly instead
    # of a relative key). Calling `.url` in that case makes the storage backend
    # blindly prepend its own base path onto that already-absolute URL, producing
    # a broken doubled URL like '.../v1/media/https://res.cloudinary.com/...'.
    # So: prefer `.name` directly whenever it's already absolute.
    name = getattr(image_file, 'name', '') or ''
    if name.startswith('http://') or name.startswith('https://'):
        url = name
    else:
        url = image_file.url

    resp = requests.get(url, timeout=8)
    resp.raise_for_status()
    return resp.content


def extract_features(image_file):
    """Extract color histogram features from an image."""
    try:
        raw_bytes = _load_image_bytes(image_file)
        img = Image.open(io.BytesIO(raw_bytes))
        img.load()  # force full decode now, inside this try block
        img = img.convert('RGB')

        img = img.resize((128, 128))
        img_array = np.array(img)

        # Color histograms for R, G, B channels
        features = []
        for channel in range(3):
            hist, _ = np.histogram(img_array[:, :, channel], bins=32, range=(0, 256))
            hist = hist.astype(np.float32)
            hist /= (hist.sum() + 1e-7)  # Normalize
            features.extend(hist)

        # Add basic statistics
        for channel in range(3):
            channel_data = img_array[:, :, channel].astype(np.float32)
            features.extend([
                channel_data.mean() / 255.0,
                channel_data.std() / 255.0,
            ])

        return np.array(features)
    except Exception:
        # logger.exception captures the full traceback even when str(e) is
        # empty (e.g. some bare OSError/decoder exceptions) - this is what
        # was hiding the real cause before.
        name = getattr(image_file, 'name', repr(image_file))
        logger.exception(f"Feature extraction error for image: {name}")
        return None


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors"""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


@api_view(['POST'])
@authentication_classes([OptionalJWTAuthentication])  # DRF runs authentication BEFORE
# permission checks, so an expired/garbage Authorization header (sent automatically by
# the frontend's axios interceptor on every request) would raise 401 here even with
# AllowAny. OptionalJWTAuthentication swallows that failure and falls back to anonymous,
# while still identifying request.user when a valid token IS present - unlike a blanket
# authentication_classes=[], which would ignore good tokens too.
@permission_classes([AllowAny])
@parser_classes([MultiPartParser])
def visual_search(request):
    """Search for similar products by uploading an image"""
    try:
        if 'image' not in request.FILES:
            return Response({'error': 'Image file is required'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_image = request.FILES['image']
        n_results = int(request.data.get('n', 8))

        # Extract features from uploaded image
        query_features = extract_features(uploaded_image)
        if query_features is None:
            return Response({'error': 'Could not process image'}, status=status.HTTP_400_BAD_REQUEST)

        # Get all active products with images
        products = Product.objects.filter(is_active=True).exclude(
            featured_image=''
        ).exclude(featured_image__isnull=True).select_related('category')[:100]

        # Compare with each product image
        results = []
        for product in products:
            try:
                if product.featured_image and product.featured_image.name:
                    product_features = extract_features(product.featured_image)
                    if product_features is not None:
                        similarity = cosine_similarity(query_features, product_features)
                        results.append((product, similarity))
            except Exception:
                continue

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        top_products = [p for p, _ in results[:n_results]]
        scores = {str(p.id): s for p, s in results[:n_results]}

        serializer = ProductListSerializer(top_products, many=True, context={'request': request})
        data = serializer.data

        # Add similarity scores
        for item in data:
            item['similarity_score'] = round(scores.get(str(item['id']), 0), 3)

        return Response({
            'results': data,
            'count': len(data),
            'message': f'Found {len(data)} visually similar products'
        })

    except Exception:
        logger.exception("Visual search error")
        return Response({'error': 'Visual search failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
