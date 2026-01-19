from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.utils import normalize_whatsapp_number


class NormalizeNumberTests(TestCase):
    def test_normalize_e164_br(self):
        self.assertEqual(normalize_whatsapp_number('(11) 98820-8134'), '+5511988208134')

    def test_normalize_fallback_digits(self):
        self.assertEqual(normalize_whatsapp_number('1234abc'), '1234')


class LoginRedirectTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def _login(self, number, password):
        return self.client.post(reverse('login'), {'whatsapp_number': number, 'password': password})

    def test_login_redirects_to_generic_dashboard(self):
        self.User.objects.create_user('+5511999999999', 'senha123', role=self.User.Role.PROFESSOR)
        response = self._login('11 99999-9999', 'senha123')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))
        follow = self.client.get(response.url, follow=True)
        self.assertEqual(follow.status_code, 200)

    def test_login_shows_error_on_failure(self):
        response = self._login('11 98820-8134', 'wrong')
        self.assertContains(response, 'Número ou senha não conferem', status_code=200)


class RBACDashboardTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def _mk_user(self, role):
        return self.User.objects.create_user('+5511990000000', 'senha123', role=role)

    def test_professor_access_allowed(self):
        user = self._mk_user(self.User.Role.PROFESSOR)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard-professor'))
        self.assertEqual(resp.status_code, 200)

    def test_professor_cannot_access_tesoureiro(self):
        user = self._mk_user(self.User.Role.PROFESSOR)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard-tesoureiro'))
        self.assertEqual(resp.status_code, 403)

    def test_redirect_dashboard_generic(self):
        user = self._mk_user(self.User.Role.RESPONSAVEL)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard'))
        self.assertRedirects(resp, reverse('dashboard-responsavel'))
