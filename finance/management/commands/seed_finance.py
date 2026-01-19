from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import User
from children.models import Child, GuardianChild
from finance.models import Fee


class Command(BaseCommand):
    help = "Seed de finanças: usuários, crianças e mensalidades"

    def handle(self, *args, **options):
        # Usuários
        tes, _ = User.objects.get_or_create(
            whatsapp_number='+559999200001', defaults={'role': User.Role.TESOUREIRO, 'first_name': 'Tesoureiro'}
        )
        tes.set_password('senha123')
        tes.role = User.Role.TESOUREIRO
        tes.save()

        dir_, _ = User.objects.get_or_create(
            whatsapp_number='+559999200002', defaults={'role': User.Role.DIRETORIA, 'first_name': 'DiretoriaFin'}
        )
        dir_.set_password('senha123')
        dir_.role = User.Role.DIRETORIA
        dir_.save()

        resp, _ = User.objects.get_or_create(
            whatsapp_number='+559999200003', defaults={'role': User.Role.RESPONSAVEL, 'first_name': 'RespFin'}
        )
        resp.set_password('senha123')
        resp.role = User.Role.RESPONSAVEL
        resp.save()

        # Crianças Turma A
        kids = []
        for idx in range(1, 3):
            child, _ = Child.objects.get_or_create(
                name=f'Fin A{idx}', defaults={'birth_date': date(2018, idx, idx), 'class_group': 'Turma A', 'active': True}
            )
            kids.append(child)
            GuardianChild.objects.get_or_create(guardian_user=resp, child=child, defaults={'relationship': 'Responsável'})

        # Mensalidades para cada criança
        months = ['2025-01', '2025-02', '2025-03']
        today = date.today()
        for child in kids:
            # pendente futuro
            Fee.objects.get_or_create(
                child=child,
                reference_month=months[0],
                defaults={'amount': Decimal('100.00'), 'due_date': today + timedelta(days=10), 'status': Fee.Status.PENDENTE},
            )
            # atrasada
            Fee.objects.get_or_create(
                child=child,
                reference_month=months[1],
                defaults={'amount': Decimal('120.00'), 'due_date': today - timedelta(days=10), 'status': Fee.Status.PENDENTE},
            )
            # isento
            Fee.objects.get_or_create(
                child=child,
                reference_month=months[2],
                defaults={'amount': Decimal('0.00'), 'due_date': today, 'status': Fee.Status.ISENTO},
            )

        self.stdout.write(self.style.SUCCESS('Seed de finanças aplicada com sucesso.'))
