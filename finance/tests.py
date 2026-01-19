from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from children.models import Child, GuardianChild
from finance.models import Fee


class FinanceTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.tes = self.User.objects.create_user('+5511999999999', 'senha123', role=self.User.Role.TESOUREIRO)
        self.resp = self.User.objects.create_user('+5511888887777', 'senha123', role=self.User.Role.RESPONSAVEL)
        self.dir = self.User.objects.create_user('+5511777777777', 'senha123', role=self.User.Role.DIRETORIA)
        self.child = Child.objects.create(name='Fin Child', birth_date='2018-01-01', class_group='Turma A')
        GuardianChild.objects.create(guardian_user=self.resp, child=self.child, relationship='Pai')

    def test_tesoureiro_generate_fees(self):
        self.client.force_login(self.tes)
        resp = self.client.post(reverse('finance-fee-new'), {
            'reference_month': '2025-04',
            'amount': '100.00',
            'due_date': (date.today() + timedelta(days=5)).isoformat(),
            'class_group': 'Turma A',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Fee.objects.filter(child=self.child, reference_month='2025-04').exists())

    def test_responsavel_sees_only_their_child(self):
        other_child = Child.objects.create(name='Outro', birth_date='2018-02-02', class_group='Turma A')
        Fee.objects.create(child=self.child, reference_month='2025-01', amount=Decimal('10.00'), due_date=date.today())
        Fee.objects.create(child=other_child, reference_month='2025-01', amount=Decimal('10.00'), due_date=date.today())
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('finance-my'))
        self.assertContains(resp, 'Fin Child')
        self.assertNotContains(resp, 'Outro')

    def test_diretoria_access_reports(self):
        self.client.force_login(self.dir)
        resp = self.client.get(reverse('finance-reports'))
        self.assertEqual(resp.status_code, 200)
