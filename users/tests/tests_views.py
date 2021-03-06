from django.test import TestCase, Client
from django.conf import settings
from users.models import OpenHumansMember
import requests_mock
from unittest.mock import mock_open, patch
from urllib.error import HTTPError
from users.views import upload_file_to_oh

OH_BASE_URL = settings.OH_BASE_URL
OH_API_BASE = OH_BASE_URL + '/api/direct-sharing'
OH_DIRECT_UPLOAD = OH_API_BASE + '/project/files/upload/direct/'
OH_DIRECT_UPLOAD_COMPLETE = OH_API_BASE + '/project/files/upload/complete/'


class IndexTestCase(TestCase):
    """
    Test cases for the index view function.
    """

    def setUp(self):
        """
        Set up the app for following test.
        """
        settings.DEBUG = True
        settings.OH_CLIENT_ID = 'foo'
        settings.OH_ACTIVITY_PAGE = 'foobar.com'
        settings.OH_REDIRECT_URI = 'foo.com'
        self.oh_member = OpenHumansMember.create(oh_id='1234567890abcdef',
                                                 access_token='foo',
                                                 refresh_token='bar',
                                                 expires_in=2000)
        self.oh_member.save()
        self.user = self.oh_member.user
        self.user.set_password('foobar')
        self.user.save()

    def test_index(self):
        """
        Tests the index view function.
        """
        c = Client()
        response = c.get('/users/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/index.html')
        self.assertEqual(response.context['client_id'], 'foo')
        self.assertEqual(response.context['oh_proj_page'], 'foobar.com')
        self.assertEqual(response.context['redirect_uri'], 'foo.com')

    def test_index_when_authenticated(self):
        """
        Tests the index view function when authenticated.
        """
        c = Client()
        c.login(username=self.user.username, password='foobar')
        response = c.get('/users/')
        self.assertRedirects(response, '/users/dashboard/',
                             status_code=302, target_status_code=200)


class DeleteTestCase(TestCase):
    """
    Test cases for the delete_account view function.
    """

    def setUp(self):
        """
        Set up the app for following test.
        """
        settings.DEBUG = True
        self.oh_member = OpenHumansMember.create(oh_id='1234567890abcdef',
                                                 access_token='foo',
                                                 refresh_token='bar',
                                                 expires_in=2000)
        self.oh_member.save()
        self.user = self.oh_member.user
        self.user.set_password('foobar')
        self.user.save()

    def test_delete(self):
        """
        Tests the delete_account view function.
        """
        c = Client()
        response = c.get('/users/delete/')
        self.assertRedirects(response, '/',
                             status_code=302, target_status_code=302)

    def test_delete_when_authenticated(self):
        """
        Tests the delete_account view function when authenticated.
        """
        c = Client()
        c.login(username=self.user.username, password='foobar')
        response = c.get('/users/delete/')
        self.assertRedirects(response, '/',
                             status_code=302, target_status_code=302)
        self.assertEqual(
            c.login(username=self.user.username, password='foobar'),
            False)


class DashboardTestCase(TestCase):
    """
    Test cases for the dashboard view function.
    """

    def setUp(self):
        """
        Set up the app for following test.
        """
        settings.DEBUG = True
        settings.OH_ACTIVITY_PAGE = 'foobar.com'
        settings.OH_CLIENT_ID = 'foo'
        self.oh_member = OpenHumansMember.create(oh_id='1234567890abcdef',
                                                 access_token='foo',
                                                 refresh_token='bar',
                                                 expires_in=2000)
        self.oh_member.save()
        self.user = self.oh_member.user
        self.user.set_password('foobar')
        self.user.save()

    def test_dashboard(self):
        """
        Tests the dashboard view function
        """
        c = Client()
        response = c.get('/users/dashboard/')
        self.assertRedirects(response, '/',
                             status_code=302, target_status_code=302)

    def test_dashboard_when_authenticated(self):
        """
        Tests the dashboard view function when authenticated
        """
        c = Client()
        c.login(username=self.user.username, password='foobar')
        response = c.get('/users/dashboard/')
        self.assertTemplateUsed(response, 'users/dashboard.html')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['section'], 'home')
        self.assertEqual(response.context['oh_proj_page'], 'foobar.com')
        self.assertEqual(response.context['oh_member'], self.oh_member)
        self.assertEqual(response.context['has_data'], False)
        self.assertEqual(response.context['client_id'], 'foo')


class AccessSwitchTestCase(TestCase):
    """
    Test cases for the access_switch view function.
    """

    def setUp(self):
        """
        Set up the app for following test.
        """
        settings.DEBUG = True
        self.oh_member = OpenHumansMember.create(oh_id='1234567890abcdef',
                                                 access_token='foo',
                                                 refresh_token='bar',
                                                 expires_in=2000,)
        self.oh_member.save()
        self.user = self.oh_member.user
        self.user.set_password('foobar')
        self.user.save()

    def test_access_switch_unauthenticated(self):
        """
        Tests the access_switch view function
        when unauthenticated.
        """
        c = Client()
        response = c.get('/users/access_switch/')
        self.assertRedirects(response, '/users/dashboard/',
                             status_code=302, target_status_code=302)

    def test_access_switch(self):
        """
        Tests the access_switch view function.
        """
        c = Client()
        c.login(username=self.user.username, password='foobar')
        retrieved = OpenHumansMember.objects.get(
            oh_id=self.user.openhumansmember.oh_id)
        self.assertEqual(retrieved.public, False)
        c.get('/users/access_switch/')
        retrieved = OpenHumansMember.objects.get(
            oh_id=self.user.openhumansmember.oh_id)
        self.assertEqual(retrieved.public, True)


class UploadTestCase(TestCase):
    """
    Tests for upload_file_to_oh and upload_old.
    """

    def setUp(self):
        """
        Set up the app for following tests
        """
        settings.DEBUG = True
        self.oh_member = OpenHumansMember.create(oh_id='1234567890abcdef',
                                                 access_token='foo',
                                                 refresh_token='bar',
                                                 expires_in=2000)
        self.oh_member.save()
        self.user = self.oh_member.user
        self.user.set_password('foobar')
        self.user.save()

    def test_upload_old(self):
        """
        Tests the upload_old function.
        """
        c = Client()
        response = c.get('/users/upload_simple/')
        self.assertRedirects(response, '/users/dashboard/',
                             status_code=302, target_status_code=302)

    def test_upload_old_authenticated(self):
        """
        Tests the upload_old function when authenticated.
        """
        c = Client()
        c.login(username=self.user.username, password='foobar')
        response = c.get('/users/upload_simple/')
        self.assertTemplateUsed(response, 'users/upload_old.html')

    def test_upload_function(self):
        """
        Tests upload feature
        """
        with requests_mock.Mocker() as m:
            # API-upload-URL
            upload_url = '{}?access_token={}'.format(
                OH_DIRECT_UPLOAD, self.oh_member.access_token)
            # mock delete-API call
            m.register_uri('POST',
                           OH_API_BASE + "/project/files/delete/",
                           status_code=200)
            # mock request 1 to initiate upload, get AWS link
            m.register_uri('POST',
                           upload_url,
                           json={'url':
                                 'http://example.com/upload',
                                 'id': 1234},
                           status_code=201)
            # mock AWS link
            m.register_uri('PUT',
                           'http://example.com/upload',
                           status_code=200)
            # mock completed link
            m.register_uri('POST',
                           OH_DIRECT_UPLOAD_COMPLETE,
                           status_code=200)
            with patch('builtins.open',
                       mock_open(read_data='foobar'),
                       create=True):
                fake_file = open('foo')
                upload_file_to_oh(self.oh_member,
                                  fake_file,
                                  {'tags': '["foo"]'})

    def test_upload_function_first_fail(self):
        """
        Tests upload feature.
        """
        with requests_mock.Mocker() as m:
            # API-upload-URL
            upload_url = '{}?access_token={}'.format(
                OH_DIRECT_UPLOAD, self.oh_member.access_token)
            # mock delete-API call
            m.register_uri('POST',
                           OH_API_BASE + "/project/files/delete/",
                           status_code=200)
            # mock request 1 to initiate upload, get AWS link
            m.register_uri('POST',
                           upload_url,
                           json={'url':
                                 'http://example.com/upload',
                                 'id': 1234},
                           status_code=404)
            # mock AWS link
            m.register_uri('PUT',
                           'http://example.com/upload',
                           status_code=200)
            # mock completed link
            m.register_uri('POST',
                           OH_DIRECT_UPLOAD_COMPLETE,
                           status_code=200)
            with patch('builtins.open',
                       mock_open(read_data='foobar'),
                       create=True):
                fake_file = open('foo')
                self.assertRaises(HTTPError, upload_file_to_oh,
                                  self.oh_member, fake_file,
                                  {'tags': '["foo"]'})

    def test_upload_function_second_fail(self):
        """
        Tests upload feature
        """
        with requests_mock.Mocker() as m:
            # API-upload-URL
            upload_url = '{}?access_token={}'.format(
                OH_DIRECT_UPLOAD, self.oh_member.access_token)
            # mock delete-API call
            m.register_uri('POST',
                           OH_API_BASE + "/project/files/delete/",
                           status_code=200)
            # mock request 1 to initiate upload, get AWS link
            m.register_uri('POST',
                           upload_url,
                           json={'url':
                                 'http://example.com/upload',
                                 'id': 1234},
                           status_code=201)
            # mock AWS link
            m.register_uri('PUT',
                           'http://example.com/upload',
                           status_code=404)
            # mock completed link
            m.register_uri('POST',
                           OH_DIRECT_UPLOAD_COMPLETE,
                           status_code=200)
            with patch('builtins.open',
                       mock_open(read_data='foobar'),
                       create=True):
                fake_file = open('foo')
                self.assertRaises(HTTPError, upload_file_to_oh,
                                  self.oh_member, fake_file,
                                  {'tags': '["foo"]'})

    def test_upload_function_third_fail(self):
        """
        Tests upload feature
        """
        with requests_mock.Mocker() as m:
            # API-upload-URL
            upload_url = '{}?access_token={}'.format(
                OH_DIRECT_UPLOAD, self.oh_member.access_token)
            # mock delete-API call
            m.register_uri('POST',
                           OH_API_BASE + "/project/files/delete/",
                           status_code=200)
            # mock request 1 to initiate upload, get AWS link
            m.register_uri('POST',
                           upload_url,
                           json={'url':
                                 'http://example.com/upload',
                                 'id': 1234},
                           status_code=201)
            # mock AWS link
            m.register_uri('PUT',
                           'http://example.com/upload',
                           status_code=200)
            # mock completed link
            m.register_uri('POST',
                           OH_DIRECT_UPLOAD_COMPLETE,
                           status_code=404)
            with patch('builtins.open',
                       mock_open(read_data='foobar'),
                       create=True):
                fake_file = open('foo')
                self.assertRaises(HTTPError, upload_file_to_oh,
                                  self.oh_member, fake_file,
                                  {'tags': '["foo"]'})


class CompleteTestCase(TestCase):
    """
    Tests for complete function.
    """

    def setUp(self):
        """
        Set up the app for following tests
        """
        settings.DEBUG = True
        self.oh_member = OpenHumansMember.create(oh_id='1234567890abcdef',
                                                 access_token='foo',
                                                 refresh_token='bar',
                                                 expires_in=2000)
        self.oh_member.save()
        self.user = self.oh_member.user
        self.user.set_password('foobar')
        self.user.save()

    def test_complete_unauthenticated(self):
        """
        Tests making a get request to complete
        when not authenticated.
        """
        with self.assertLogs(logger='users.views', level='DEBUG') as log:
            c = Client()
            response = c.get("/users/complete/", {'code': 'mytestcode'})
        self.assertIn(
                    "Invalid code exchange. User returned to start page.",
                    log.output[len(log.output)-1])
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/',
                             status_code=302, target_status_code=302)


class RegenerategraphsTestCase(TestCase):
    """
    Tests regenerate_graphs.
    """

    def setUp(self):
        """
        Set up the app for following tests
        """
        settings.DEBUG = True
        self.oh_member = OpenHumansMember.create(oh_id='1234567890abcdef',
                                                 access_token='foo',
                                                 refresh_token='bar',
                                                 expires_in=2000)
        self.oh_member.save()
        self.user = self.oh_member.user
        self.user.set_password('foobar')
        self.user.save()

    def test_regenerate_graphs_get_unauthenticated(self):
        """
        Test making a get request to regenerate_graphs
        when not authenticated.
        """
        c = Client()
        response = c.get('/users/regenerate/')
        self.assertRedirects(response, '/users/dashboard/',
                             status_code=302, target_status_code=302)

    def test_regenerate_graphs_get_authenticated(self):
        """
        Test making a get request to regenerate_graphs
        when authenticated.
        """
        c = Client()
        c.login(username=self.user.username, password='foobar')
        response = c.get('/users/regenerate/')
        self.assertRedirects(response, '/users/dashboard/',
                             status_code=302, target_status_code=200)
