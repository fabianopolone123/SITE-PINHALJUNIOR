from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from children.models import Child, GuardianChild
from curriculum.models import ChildProgress, ClassSchedule, ContentItem


class CurriculumTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.prof = self.User.objects.create_user('+5511999999999', 'senha123', role=self.User.Role.PROFESSOR)
        self.resp = self.User.objects.create_user('+5511888877777', 'senha123', role=self.User.Role.RESPONSAVEL)
        self.child = Child.objects.create(name='Aluno 1', birth_date='2018-01-01', class_group='Turma A')
        GuardianChild.objects.create(guardian_user=self.resp, child=self.child, relationship='Pai')
        self.content = ContentItem.objects.create(title='Item 1', order=1, module='U1', active=True)

    def test_professor_can_save_progress(self):
        self.client.force_login(self.prof)
        # create selection form post
        resp = self.client.post(reverse('curriculum-progress'), {
            'class_group': 'Turma A',
            'content_item': self.content.id,
            'save': '1',
            f'status_{self.child.id}': 'CONCLUIDO',
            f'note_{self.child.id}': 'Ok',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ChildProgress.objects.count(), 1)

    def test_responsavel_sees_only_own_children(self):
        other_child = Child.objects.create(name='Aluno 2', birth_date='2018-02-02', class_group='Turma A')
        ChildProgress.objects.create(child=other_child, content_item=self.content, status=ChildProgress.Status.CONCLUIDO)
        ChildProgress.objects.create(child=self.child, content_item=self.content, status=ChildProgress.Status.EM_ANDAMENTO)
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('curriculum-my'))
        self.assertContains(resp, 'Aluno 1')
        self.assertNotContains(resp, 'Aluno 2')

    def test_responsavel_forbidden_on_other_child(self):
        other_child = Child.objects.create(name='Aluno 3', birth_date='2018-03-03', class_group='Turma A')
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('curriculum-child-progress', args=[other_child.id]))
        self.assertEqual(resp.status_code, 403)
