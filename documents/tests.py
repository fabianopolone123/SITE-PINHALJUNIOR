from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from children.models import Child, GuardianChild
from documents.models import ChildDocument, DocumentRequest, DocumentType


class DocumentsTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.secretaria = self.User.objects.create_user('+5511999999999', 'senha123', role=self.User.Role.SECRETARIA)
        self.diretoria = self.User.objects.create_user('+5511888887777', 'senha123', role=self.User.Role.DIRETORIA)
        self.resp = self.User.objects.create_user('+5511777777777', 'senha123', role=self.User.Role.RESPONSAVEL)
        self.child = Child.objects.create(name='Doc Child', birth_date='2018-01-01', class_group='Turma A')
        GuardianChild.objects.create(guardian_user=self.resp, child=self.child, relationship='Pai')
        self.doc_type = DocumentType.objects.create(name='RG', required=True)
        self.child_doc = ChildDocument.objects.create(child=self.child, document_type=self.doc_type)

    def test_secretaria_access_overview(self):
        self.client.force_login(self.secretaria)
        resp = self.client.get(reverse('documents-overview'))
        self.assertEqual(resp.status_code, 200)

    def test_secretaria_creates_request(self):
        self.client.force_login(self.secretaria)
        resp = self.client.get(reverse('documents-request', args=[self.child.id, self.doc_type.id]))
        self.assertEqual(resp.status_code, 302)  # redirect to wa.me
        self.assertEqual(DocumentRequest.objects.count(), 1)

    def test_responsavel_only_own_child(self):
        other = Child.objects.create(name='Outro', birth_date='2018-02-02', class_group='Turma A')
        self.client.force_login(self.resp)
        resp = self.client.get(reverse('documents-child', args=[other.id]))
        self.assertEqual(resp.status_code, 403)

