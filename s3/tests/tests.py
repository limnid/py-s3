import unittest

from pyramid import testing


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_main_view(self):
        from .views import main_view
        request = testing.DummyRequest()
        info = main_view(request)
        self.assertEqual(info['project'], 's3')
