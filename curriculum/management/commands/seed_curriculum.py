from datetime import date, timedelta

from django.core.management.base import BaseCommand

from accounts.models import User
from children.models import Child, GuardianChild
from curriculum.models import ChildProgress, ClassSchedule, ContentItem


class Command(BaseCommand):
    help = "Seed de currículo: usuários, crianças, conteúdos, cronograma e progresso"

    def handle(self, *args, **options):
        # Usuários
        prof, _ = User.objects.get_or_create(whatsapp_number='+559999000001', defaults={'role': User.Role.PROFESSOR, 'first_name': 'Professor'})
        prof.set_password('senha123')
        prof.role = User.Role.PROFESSOR
        prof.save()

        dir_, _ = User.objects.get_or_create(whatsapp_number='+559999000002', defaults={'role': User.Role.DIRETORIA, 'first_name': 'Diretoria'})
        dir_.set_password('senha123')
        dir_.role = User.Role.DIRETORIA
        dir_.save()

        resp, _ = User.objects.get_or_create(whatsapp_number='+559999000003', defaults={'role': User.Role.RESPONSAVEL, 'first_name': 'Responsável'})
        resp.set_password('senha123')
        resp.role = User.Role.RESPONSAVEL
        resp.save()

        # Crianças Turma A
        kids = []
        for idx in range(1, 4):
            child, _ = Child.objects.get_or_create(
                name=f'Aventureiro A{idx}',
                defaults={'birth_date': date(2018, idx, idx), 'class_group': 'Turma A', 'active': True},
            )
            kids.append(child)
            GuardianChild.objects.get_or_create(guardian_user=resp, child=child, defaults={'relationship': 'Responsável'})

        # Conteúdos
        contents = []
        for i in range(1, 7):
            item, _ = ContentItem.objects.get_or_create(
                order=i,
                title=f'Conteúdo {i}',
                defaults={'module': 'Unidade 1', 'active': True},
            )
            contents.append(item)

        # Cronograma Turma A
        today = date.today()
        for idx, item in enumerate(contents[:3]):
            ClassSchedule.objects.get_or_create(
                class_group='Turma A',
                content_item=item,
                planned_date=today + timedelta(days=idx),
                defaults={'status': ClassSchedule.Status.PLANEJADO, 'created_by_user': dir_},
            )

        # Progresso: para cada criança, 3 conteúdos com status diferentes
        for child in kids:
            statuses = [
                (contents[0], ChildProgress.Status.CONCLUIDO),
                (contents[1], ChildProgress.Status.EM_ANDAMENTO),
                (contents[2], ChildProgress.Status.NAO_INICIADO),
            ]
            for item, status in statuses:
                obj, _ = ChildProgress.objects.get_or_create(child=child, content_item=item)
                obj.status = status
                obj.note = f'Status {status}'
                obj.marked_by_user = prof if item.order % 2 == 0 else dir_
                obj.save()

        self.stdout.write(self.style.SUCCESS('Seed de currículo aplicada com sucesso.'))
