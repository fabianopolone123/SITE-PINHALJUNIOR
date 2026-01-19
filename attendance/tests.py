from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from attendance.models import AttendanceRecord, AttendanceSession
from children.models import Child, GuardianChild


class AttendanceTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.staff = self.User.objects.create_user('+5511999999999', 'senha123', role=self.User.Role.PROFESSOR)
        self.resp = self.User.objects.create_user('+5511988887777', 'senha123', role=self.User.Role.RESPONSAVEL)
        self.child1 = Child.objects.create(name='Filho 1', birth_date='2018-01-01', class_group='Lobos')
        self.child2 = Child.objects.create(name='Filho 2', birth_date='2018-02-02', class_group='Lobos')
        GuardianChild.objects.create(guardian_user=self.resp, child=self.child1, relationship='Pai')

    def test_staff_can_create_session(self):
        self.client.force_login(self.staff)
        resp = self.client.post(reverse('attendance-session-new'), {
            'date': '2024-01-01',
            'type': 'REUNIAO',
            'class_group': 'Lobos',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(AttendanceSession.objects.count(), 1)

    def test_responsavel_cannot_take_attendance(self):
        session = AttendanceSession.objects.create(date='2024-01-01', type='REUNIAO', class_group='Lobos')
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('attendance-take', args=[session.id]))
        self.assertEqual(resp.status_code, 403)

    def test_responsavel_sees_only_their_children(self):
        session = AttendanceSession.objects.create(date='2024-01-01', type='REUNIAO', class_group='Lobos')
        AttendanceRecord.objects.create(session=session, child=self.child1, present=True)
        AttendanceRecord.objects.create(session=session, child=self.child2, present=False)
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('attendance-my'))
        self.assertContains(resp, 'Filho 1')
        self.assertNotContains(resp, 'Filho 2')
