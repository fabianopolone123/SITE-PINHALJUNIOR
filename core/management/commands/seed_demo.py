import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from accounts.models import User
from children.models import Child, GuardianChild
from attendance.models import AttendanceSession, AttendanceRecord
from points.models import PointsLedger
from finance.models import Fee
from documents.models import DocumentType, ChildDocument, DocumentRequest
from store.models import Category, Product


class Command(BaseCommand):
    help = "Popula dados fictícios para demonstrar presenças, pontos, financeiro e documentos."

    def handle(self, *args, **options):
        UserModel = get_user_model()

        # Usuários
        users_info = [
            ('+550001000001', 'Ana', 'Silva', User.Role.DIRETORIA),
            ('+550001000002', 'Bruno', 'Alves', User.Role.TESOUREIRO),
            ('+550001000003', 'Carla', 'Souza', User.Role.SECRETARIA),
            ('+550001000004', 'Diego', 'Lima', User.Role.PROFESSOR),
            ('+550001000005', 'Eva', 'Melo', User.Role.RESPONSAVEL),
        ]
        users = {}
        for phone, first, last, role in users_info:
            user, created = UserModel.objects.get_or_create(
                whatsapp_number=phone,
                defaults={'first_name': first, 'last_name': last, 'role': role},
            )
            if created:
                user.set_password('demo123')
                user.save()
            users[role] = user

        # Crianças
        today = timezone.localdate()
        kids_info = [
            ('João Aventureiro', today.replace(year=today.year - 6), 'Abelhinhas Laboriosas'),
            ('Maria Exploradora', today.replace(year=today.year - 7), 'Luminares'),
            ('Pedro Valente', today.replace(year=today.year - 8), 'Edificadores'),
        ]
        kids = []
        for name, birth, cls in kids_info:
            child, _ = Child.objects.get_or_create(
                name=name,
                defaults={'birth_date': birth, 'class_group': cls, 'active': True},
            )
            kids.append(child)
            GuardianChild.objects.get_or_create(
                guardian_user=users[User.Role.RESPONSAVEL],
                child=child,
                defaults={'relationship': 'Responsável'},
            )

        # Presenças
        session1, _ = AttendanceSession.objects.get_or_create(
            date=today,
            type=AttendanceSession.Type.REUNIAO,
            class_group='Todas',
            defaults={'created_by_user': users[User.Role.PROFESSOR]},
        )
        session2, _ = AttendanceSession.objects.get_or_create(
            date=today - datetime.timedelta(days=7),
            type=AttendanceSession.Type.AULA,
            class_group='Todas',
            defaults={'created_by_user': users[User.Role.PROFESSOR]},
        )
        for child in kids:
            AttendanceRecord.objects.get_or_create(
                session=session1,
                child=child,
                defaults={'present': True, 'marked_by_user': users[User.Role.PROFESSOR]},
            )
            AttendanceRecord.objects.get_or_create(
                session=session2,
                child=child,
                defaults={'present': False, 'marked_by_user': users[User.Role.PROFESSOR], 'note': 'Faltou'},
            )

        # Pontos
        for child in kids:
            PointsLedger.objects.get_or_create(
                child=child,
                points=10,
                reason='Boa participação',
                created_by_user=users[User.Role.PROFESSOR],
            )
            PointsLedger.objects.get_or_create(
                child=child,
                points=-2,
                reason='Esqueceu material',
                created_by_user=users[User.Role.PROFESSOR],
            )

        # Financeiro
        ref_months = ['2025-01', '2025-02', '2025-03']
        for child in kids:
            for idx, ref in enumerate(ref_months):
                due_date = today.replace(day=10, month=idx + 1 if idx + 1 <= 12 else 12)
                base_amount = 30
                discount = 5 if idx == 0 else 0
                final_amount = base_amount - discount
                Fee.objects.get_or_create(
                    child=child,
                    reference_month=ref,
                    defaults={
                        'amount': base_amount,
                        'discount_amount': discount,
                        'final_amount': final_amount,
                        'due_date': due_date,
                        'status': Fee.Status.PENDENTE,
                    },
                )

        # Documentos
        doc_types_data = [
            ('RG/Certidão', True, None),
            ('Ficha Médica', True, 365),
            ('Autorização', True, 365),
        ]
        doc_types = []
        for name, required, validity in doc_types_data:
            dt, _ = DocumentType.objects.get_or_create(
                name=name,
                defaults={'required': required, 'validity_days': validity, 'active': True},
            )
            doc_types.append(dt)

        for child in kids:
            for dt in doc_types:
                status = ChildDocument.Status.RECEBIDO if dt.name == 'RG/Certidão' else ChildDocument.Status.PENDENTE
                received_date = today - datetime.timedelta(days=10) if status == ChildDocument.Status.RECEBIDO else None
                ChildDocument.objects.get_or_create(
                    child=child,
                    document_type=dt,
                    defaults={
                        'status': status,
                        'received_date': received_date,
                        'valid_until': (received_date + datetime.timedelta(days=dt.validity_days))
                        if received_date and dt.validity_days
                        else None,
                        'updated_by_user': users[User.Role.SECRETARIA],
                    },
                )

        # Requests de documentos (cobrança)
        DocumentRequest.objects.get_or_create(
            child=kids[0],
            document_type=doc_types[1],
            sent_to_user=users[User.Role.RESPONSAVEL],
            sent_by_user=users[User.Role.SECRETARIA],
            channel=DocumentRequest.Channel.WHATSAPP,
            status=DocumentRequest.Status.ENVIADO,
            message='Por favor, envie a Ficha Médica atualizada.',
        )

        # Loja - categorias e produtos demo
        cat_vest, _ = Category.objects.get_or_create(name='Uniformes', defaults={'description': 'Roupas do clube'})
        cat_mat, _ = Category.objects.get_or_create(name='Materiais', defaults={'description': 'Materiais de campo'})
        products_data = [
            {
                'name': 'Camiseta do Clube',
                'description': 'Camiseta oficial, tamanhos P/M/G',
                'price': 50,
                'stock': 20,
                'category': cat_vest,
                'image_url': 'https://picsum.photos/seed/camiseta/800/600',
            },
            {
                'name': 'Lenço Aventureiro',
                'description': 'Lenço azul com bordado',
                'price': 25,
                'stock': 30,
                'category': cat_vest,
                'image_url': 'https://picsum.photos/seed/lenco/800/600',
            },
            {
                'name': 'Cantina de Água',
                'description': 'Garrafa 600ml personalizada',
                'price': 35,
                'stock': 15,
                'category': cat_mat,
                'image_url': 'https://picsum.photos/seed/cantina/800/600',
            },
            {
                'name': 'Mochila Aventureira',
                'description': 'Mochila resistente para trilhas',
                'price': 120,
                'stock': 10,
                'category': cat_mat,
                'image_url': 'https://picsum.photos/seed/mochila/800/600',
            },
            {
                'name': 'Caderno de Campo',
                'description': 'Caderno para anotações e atividades',
                'price': 18,
                'stock': 40,
                'category': cat_mat,
                'image_url': 'https://picsum.photos/seed/caderno/800/600',
            },
            {
                'name': 'Botton do Clube',
                'description': 'Pin metálico personalizado',
                'price': 8,
                'stock': 50,
                'category': cat_vest,
                'image_url': 'https://picsum.photos/seed/botton/800/600',
            },
            {
                'name': 'Pulseira Colorida',
                'description': 'Pulseira de silicone temática',
                'price': 12,
                'stock': 60,
                'category': cat_vest,
                'image_url': 'https://picsum.photos/seed/pulseira/800/600',
            },
        ]
        for data in products_data:
            data.setdefault('active', True)
            variants = []
            if data['name'] == 'Camiseta do Clube':
                variants = [
                    ('P', 50, 10),
                    ('M', 52, 8),
                    ('G', 54, 6),
                ]
            elif data['name'] == 'Lenço Aventureiro':
                variants = [('Único', 25, 30)]
            elif data['name'] == 'Cantina de Água':
                variants = [('Azul', 35, 10), ('Vermelha', 37, 5)]
            product, _ = Product.objects.update_or_create(name=data['name'], defaults=data)
            product.variants.all().delete()
            for name, price, stock in variants:
                product.variants.create(name=name, price=price, stock=stock, active=True)

        self.stdout.write(self.style.SUCCESS('Dados demo populados.'))
