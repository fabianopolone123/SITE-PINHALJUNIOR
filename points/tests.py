from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from children.models import Child, GuardianChild
from points.models import PointsLedger


class PointsTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.staff = self.User.objects.create_user('+5511999999999', 'senha123', role=self.User.Role.PROFESSOR)
        self.resp = self.User.objects.create_user('+5511988887777', 'senha123', role=self.User.Role.RESPONSAVEL)
        self.child1 = Child.objects.create(name='Filho 1', birth_date='2018-01-01', class_group='Lobos')
        self.child2 = Child.objects.create(name='Filho 2', birth_date='2018-02-02', class_group='Lobos')
        GuardianChild.objects.create(guardian_user=self.resp, child=self.child1, relationship='Pai')

    def test_staff_create_individual(self):
        self.client.force_login(self.staff)
        resp = self.client.post(reverse('points-add-individual'), {
            'child': self.child1.id,
            'points': 10,
            'reason': 'Bom comportamento',
            'category': 'Comportamento',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(PointsLedger.objects.count(), 1)

    def test_staff_create_batch(self):
        self.client.force_login(self.staff)
        resp = self.client.post(reverse('points-add-batch'), {
            'class_group': 'Lobos',
            'points': 5,
            'reason': 'Atividade em grupo',
            'category': 'Equipe',
            'children': [self.child1.id, self.child2.id],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(PointsLedger.objects.count(), 2)

    def test_responsavel_cannot_access_add(self):
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('points-add-individual'))
        self.assertEqual(resp.status_code, 403)

    def test_responsavel_sees_only_their_children(self):
        PointsLedger.objects.create(child=self.child1, points=5, reason='Teste', created_by_user=self.staff)
        PointsLedger.objects.create(child=self.child2, points=8, reason='Teste2', created_by_user=self.staff)
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('points-my'))
        self.assertContains(resp, 'Filho 1')
        self.assertNotContains(resp, 'Filho 2')
