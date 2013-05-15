from django.core.cache import cache
from django.utils.functional import wraps
from cache_helper import utils


def cached(timeout):
    def get_key(*args, **kwargs):
        return utils.sanitize_key(utils._cache_key(*args, **kwargs))

    def _cached(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_type = utils._func_type(func)
            if not hasattr(wrapper, '_full_name'):
                name, _args = utils._func_info(func, args)
                wrapper._full_name = name

            key = get_key(wrapper._full_name, func_type, args, kwargs)
            value = cache.get(key)

            if value is None:
                value = func(*args, **kwargs)
                cache.set(key, value, timeout)

            return value

        return wrapper
    return _cached
