import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aventureiros.settings')
import django
django.setup()

from accounts.models import User
from children.models import Child, GuardianChild
from finance.models import Fee

user, created = User.objects.get_or_create(whatsapp_number='+5511999990000', defaults={'role': 'RESPONSAVEL'})
if created:
    user.set_password('testpass')
    user.save()
child, _ = Child.objects.get_or_create(name='Test Child', birth_date='2015-01-01')
GuardianChild.objects.get_or_create(guardian_user=user, child=child)
Fee.objects.get_or_create(child=child, reference_month='2025-01', defaults={'amount': 100, 'final_amount': 100, 'due_date': '2025-01-10', 'status': 'PENDENTE'})
print('Setup done', user.id, child.id)
