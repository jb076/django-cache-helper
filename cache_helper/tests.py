"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

"""
from django.test import TestCase
from django.core.cache import cache

from cache_helper import settings
from decorators import cached
from utils import _func_type
from exceptions import CacheKeyCreationError

@cached(60*60)
def foo(a, b):
    return a + b


class Vegetable(object):
    def __init__(self, name):
        self.name = name

    def fun_math(self, a, b):
        return a + b

    @classmethod
    def add_sweet_letter(cls, a):
        return cls.__name__ + a


class Fruit(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'MyNameIs{0}'.format(self.name)

    @cached(60*60)
    def fun_math(self, a, b):
        return a + b

    @cached(60*60)
    def take_then_give_back(self, a):
        return a

    @property
    @cached(60*60)
    def is_green(self):
        if self.name == 'Apple':
            return True
        return False

    @classmethod
    @cached(60*60)
    def add_sweet_letter(cls, a):
        return cls.__name__ + a


class FuncTypeTest(TestCase):
    """
    Test make sure functions catch right type
    """
    celery = Vegetable('Celery')

    def assertFuncType(self, func, tp):
        self.assertEqual(_func_type(func), tp)

    def test_func(self):
        self.assertFuncType(foo, 'function')

    def test_meth(self):
        self.assertFuncType(self.celery.fun_math, 'method')

    def test_cls(self):
        self.assertFuncType(Vegetable.add_sweet_letter, 'class_method')


class BasicCacheTestCase(TestCase):
    def test_function_cache(self):
        x = foo(1, 2)
        self.assertTrue('cache_helper.tests.foo:14;1,2,;' in cache)

class MultipleCallsDiffParamsTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apple = Fruit('Apple')
        cls.cherry = Fruit('Cherry')

    def test_two_models(self):
        # Call first time and place in cache
        apple_val = self.apple.fun_math(10, 10)
        cherry_val = self.cherry.fun_math(15, 10)

        self.assertEqual(self.apple.fun_math(10, 10), apple_val)
        self.assertEqual(self.cherry.fun_math(15, 10), cherry_val)

    def test_class_method(self):
        apple_val = Fruit.add_sweet_letter('a')
        cherry_val = Fruit.add_sweet_letter('c')

        self.assertTrue("cache_helper.tests.Fruit.add_sweet_letter:53;a,;" in cache)
        self.assertTrue("cache_helper.tests.Fruit.add_sweet_letter:53;c,;" in cache)
        self.assertEqual(Fruit.add_sweet_letter('a'), 'Fruita')
        self.assertEqual(Fruit.add_sweet_letter('c'), 'Fruitc')

class KeyLengthTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apple = Fruit('Apple')

    def test_keys_are_truncated_beyond_250_chars(self):
        try:
            apple_val = self.apple.fun_math(('a' * 200), ('b' * 200))
            self.assertTrue(isinstance(apple_val, str))
        except Exception:
            self.fail('Keys are not being correctly truncated.')


class KeyCreationTestCase(TestCase):
    def setUp(self):
        self.apple = Fruit('Apple')
        self.cherry = Fruit('Cherry')

    def tearDown(self):
        settings.MAX_DEPTH = 2

    def test_args_kwargs_properly_convert_to_string(self):
        """
        Surface level objects are serialized correctly with default settings...
        """
        same_cherry = self.apple.take_then_give_back(self.cherry)
        self.assertTrue('cache_helper.tests.Fruit.take_then_give_back:42;mynameisapple,mynameischerry,;' in cache)

    def test_dict_args_properly_convert_to_string(self):
        same_cherry = self.apple.take_then_give_back({1: self.cherry})
        self.assertTrue('cache_helper.tests.Fruit.take_then_give_back:42;mynameisapple,1:mynameischerry,,;' in cache)

    def test_list_args_properly_convert_to_string(self):
        same_cherry = self.apple.take_then_give_back([self.cherry])
        self.assertTrue('cache_helper.tests.Fruit.take_then_give_back:42;mynameisapple,mynameischerry,,;' in cache)

    def test_raises_depth_error(self):
        settings.MAX_DEPTH = 0
        with self.assertRaises(CacheKeyCreationError):
            same_cherry = self.apple.take_then_give_back([self.cherry])

