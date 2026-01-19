from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Child, GuardianChild


class ChildrenAccessTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.staff = self.User.objects.create_user('+5511999999999', 'senha123', role=self.User.Role.SECRETARIA)
        self.resp = self.User.objects.create_user('+5511988887777', 'senha123', role=self.User.Role.RESPONSAVEL)
        self.child1 = Child.objects.create(name='Aventureiro 1', birth_date='2018-01-01', class_group='Lobos')
        self.child2 = Child.objects.create(name='Aventureiro 2', birth_date='2017-02-02', class_group='Lobos')
        GuardianChild.objects.create(guardian_user=self.resp, child=self.child1, relationship='Pai')

    def test_staff_can_list_children(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('children-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Aventureiro 1')

    def test_responsavel_cannot_list_children(self):
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('children-list'))
        self.assertEqual(resp.status_code, 403)

    def test_responsavel_only_sees_own_children(self):
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('children-meus'))
        self.assertContains(resp, 'Aventureiro 1')
        self.assertNotContains(resp, 'Aventureiro 2')
