from django.conf import settings

MAX_DEPTH = getattr(settings, 'CACHE_HELPER_MAX_DEPTH', 2)

CACHE_MIDDLEWARE_KEY_PREFIX = getattr(settings, 'CACHE_MIDDLEWARE_KEY_PREFIX', '')