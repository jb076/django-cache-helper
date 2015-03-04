import unicodedata
from hashlib import sha256

from django.core.cache import cache

from cache_helper import settings
from cache_helper.exceptions import CacheKeyCreationError

# List of Control Characters not useable by memcached
CONTROL_CHARACTERS = set([chr(i) for i in range(0, 33)])
CONTROL_CHARACTERS.add(chr(127))

def sanitize_key(key, max_length=250):
    """
    Truncates key to keep it under memcached char limit.  Replaces with hash.
    Remove control characters b/c of memcached restriction on control chars.
    """
    key = ''.join([c for c in key if c not in CONTROL_CHARACTERS])
    key_length = len(key)
    # django memcached backend will, by default, add a prefix. Account for this in max
    # key length. '%s:%s:%s'.format()
    version_length = len(str(getattr(cache, 'version', '')))
    prefix_length = len(settings.CACHE_MIDDLEWARE_KEY_PREFIX)
    # +2 for the colons
    max_length -= (version_length + prefix_length + 2)
    if key_length > max_length:
        the_hash = sha256(key).hexdigest()
        # sha256 always 64 chars.
        key = key[:max_length - 64] + the_hash
    return key


def _sanitize_args(args=[], kwargs={}):
    """
    Creates unicode key from all kwargs/args
        -Note: comma separate args in order to prevent poo(1,2), poo(12, None) corner-case collisions...
    """
    key = ";{0};{1}"
    kwargs_key = ""
    args_key = _plumb_collections(args)
    kwargs_key = _plumb_collections(kwargs)
    return key.format(args_key, kwargs_key)


def _func_type(func):
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    if len(argnames) > 0:
        if argnames[0] == 'self':
            return 'method'
        elif argnames[0] == 'cls':
            return 'class_method'
    return 'function'


def get_normalized_term(term, dash_replacement=''):
    term = unicode(str(term), encoding='utf-8')
    term = unicodedata.normalize('NFKD', term).encode('ascii', 'ignore')
    term = term.lower()
    term = term.strip()
    return term


def _func_info(func, args):
    func_type = _func_type(func)
    lineno = ":%s" % func.func_code.co_firstlineno

    if func_type == 'function':
        name = ".".join([func.__module__, func.__name__]) + lineno
        return name
    elif func_type == 'class_method':
        class_name = args[0].__name__
    else:
        class_name = args[0].__class__.__name__
    name = ".".join([func.__module__, class_name, func.__name__]) + lineno
    return name


def _cache_key(func_name, func_type, args, kwargs):
    if func_type in ['method', 'function']:
        args_string = _sanitize_args(args, kwargs)
    elif func_type == 'class_method':
        args_string = _sanitize_args(args[1:], kwargs)
    key = '%s%s' % (func_name, args_string)
    return key

def _plumb_collections(item, level=0):
    if settings.MAX_DEPTH is not None and level > settings.MAX_DEPTH:
        raise CacheKeyCreationError('Function args or kwargs have too many nested collections for current MAX_DEPTH')
    else:
        level += 1
    if hasattr(item, '__iter__'):
        return_string = ''
        if hasattr(item, 'iteritems'):
            for k, v in item.iteritems():
                v = _plumb_collections(v, level)
                item_bit = '{0}:{1},'.format(k, v)
                return_string += item_bit
            return get_normalized_term(return_string)
        else:
            try:
                iterator = item.__iter__()
                while True:
                    item_bit = '{0},'.format(_plumb_collections(iterator.next(), level))
                    return_string += item_bit
            except StopIteration:
                return get_normalized_term(return_string)
    else:
        return get_normalized_term(item)
