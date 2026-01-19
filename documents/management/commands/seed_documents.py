from datetime import date, timedelta

from django.core.management.base import BaseCommand

from accounts.models import User
from children.models import Child, GuardianChild
from documents.models import ChildDocument, DocumentRequest, DocumentType


class Command(BaseCommand):
    help = "Seed de documentos: usuários, crianças, tipos, docs e solicitações"

    def handle(self, *args, **options):
        # Usuários
        secretaria, _ = User.objects.get_or_create(
            whatsapp_number='+559999100001', defaults={'role': User.Role.SECRETARIA, 'first_name': 'Secretaria'}
        )
        secretaria.set_password('senha123')
        secretaria.role = User.Role.SECRETARIA
        secretaria.save()

        diretoria, _ = User.objects.get_or_create(
            whatsapp_number='+559999100002', defaults={'role': User.Role.DIRETORIA, 'first_name': 'Diretoria'}
        )
        diretoria.set_password('senha123')
        diretoria.role = User.Role.DIRETORIA
        diretoria.save()

        responsavel, _ = User.objects.get_or_create(
            whatsapp_number='+559999100003', defaults={'role': User.Role.RESPONSAVEL, 'first_name': 'Responsável'}
        )
        responsavel.set_password('senha123')
        responsavel.role = User.Role.RESPONSAVEL
        responsavel.save()

        # Crianças Turma A
        kids = []
        for idx in range(1, 3):
            child, _ = Child.objects.get_or_create(
                name=f'Doc A{idx}',
                defaults={'birth_date': date(2018, idx, idx), 'class_group': 'Turma A', 'active': True},
            )
            kids.append(child)
            GuardianChild.objects.get_or_create(guardian_user=responsavel, child=child, defaults={'relationship': 'Responsável'})

        # Tipos de documento
        doc_types_data = [
            ('RG/Certidão', True, None),
            ('Ficha Médica', True, 365),
            ('Autorização', True, 365),
            ('Foto 3x4', False, None),
        ]
        doc_types = []
        for name, required, validity in doc_types_data:
            dt, _ = DocumentType.objects.get_or_create(name=name, defaults={'required': required, 'validity_days': validity, 'active': True})
            doc_types.append(dt)

        # ChildDocument estados variados
        today = date.today()
        for child in kids:
            for idx, dt in enumerate(doc_types):
                cd, _ = ChildDocument.objects.get_or_create(child=child, document_type=dt)
                if idx == 0:
                    cd.status = ChildDocument.Status.RECEBIDO
                    cd.received_date = today - timedelta(days=10)
                elif idx == 1:
                    cd.status = ChildDocument.Status.VENCIDO
                    cd.received_date = today - timedelta(days=400)
                    cd.valid_until = today - timedelta(days=35)
                elif idx == 2:
                    cd.status = ChildDocument.Status.REJEITADO
                    cd.note = 'Assinatura faltando'
                else:
                    cd.status = ChildDocument.Status.PENDENTE
                cd.apply_validity()
                cd.updated_by_user = secretaria
                cd.save()

        # Solicitações
        for child in kids:
            for dt in doc_types[:2]:
                DocumentRequest.objects.get_or_create(
                    child=child,
                    document_type=dt,
                    sent_to_user=responsavel,
                    sent_by_user=secretaria,
                    channel=DocumentRequest.Channel.WHATSAPP,
                    message=f'Favor enviar {dt.name} de {child.name}',
                    defaults={'status': DocumentRequest.Status.ENVIADO},
                )

        self.stdout.write(self.style.SUCCESS('Seed de documentos aplicada com sucesso.'))
