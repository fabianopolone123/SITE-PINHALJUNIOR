from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from accounts.utils import normalize_whatsapp_number
from children.models import Child, GuardianChild


class AdventureLoginForm(forms.Form):
    whatsapp_number = forms.CharField(
        label='Número de WhatsApp',
        max_length=20,
        widget=forms.TextInput(
            attrs={
                'placeholder': '14988208134',
                'inputmode': 'tel',
                'autocomplete': 'username',
                'class': 'input',
            }
        ),
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Digite sua senha',
                'autocomplete': 'current-password',
                'class': 'input',
            }
        ),
    )

    def clean_whatsapp_number(self):
        number = self.cleaned_data['whatsapp_number']
        normalized = normalize_whatsapp_number(number)
        if not normalized:
            raise ValidationError('Informe um número de WhatsApp válido.')
        return normalized


class UserCreateForm(forms.Form):
    ROLE_CHOICES = [
        ('ADM', 'ADM'),
        ('DIRETORIA', 'Diretoria'),
        ('SECRETARIA', 'Secretaria'),
        ('TESOUREIRO', 'Tesoureiro'),
        ('PROFESSOR', 'Professor'),
        ('RESPONSAVEL', 'Responsável'),
    ]

    whatsapp_number = forms.CharField(label='WhatsApp', max_length=20)
    first_name = forms.CharField(label='Nome', max_length=150, required=False)
    last_name = forms.CharField(label='Sobrenome', max_length=150, required=False)
    role = forms.ChoiceField(label='Perfil', choices=ROLE_CHOICES)
    extra_roles = forms.MultipleChoiceField(
        label='Perfis adicionais',
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)
    new_children = forms.CharField(
        label='Criar novas crianças (uma por linha: Nome;AAAA-MM-DD)',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def clean_whatsapp_number(self):
        number = self.cleaned_data['whatsapp_number']
        normalized = normalize_whatsapp_number(number)
        if not normalized:
            raise ValidationError('Informe um número válido.')
        return normalized

    def _assign_group(self, user, role, extras=None):
        extras = extras or []
        group_map = {
            'DIRETORIA': 'Diretoria',
            'SECRETARIA': 'Secretaria',
            'TESOUREIRO': 'Tesoureiro',
            'PROFESSOR': 'Professor',
            'RESPONSAVEL': 'Responsavel',
            'ADM': 'ADM',
        }
        group_names = []
        for r in {role, *extras}:
            g = group_map.get(r)
            if g:
                group_names.append(g)
        groups = [Group.objects.get_or_create(name=g)[0] for g in group_names]
        user.groups.set(groups)

    def save(self):
        User = get_user_model()
        data = self.cleaned_data
        user, created = User.objects.get_or_create(
            whatsapp_number=data['whatsapp_number'],
            defaults={
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'role': data['role'],
            },
        )
        user.first_name = data.get('first_name')
        user.last_name = data.get('last_name')
        user.role = data['role']
        user.set_password(data['password'])
        user.save()

        extras = data.get('extra_roles') or []
        self._assign_group(user, data['role'], extras)

        if data['role'] == 'RESPONSAVEL':
            import datetime

            new_children_raw = data.get('new_children', '').strip()
            for line in new_children_raw.splitlines():
                parts = [p.strip() for p in line.split(';') if p.strip()]
                if not parts:
                    continue
                name = parts[0]
                birth_date = None
                if len(parts) > 1:
                    try:
                        birth_date = datetime.date.fromisoformat(parts[1])
                    except ValueError:
                        birth_date = None
                if not birth_date:
                    birth_date = datetime.date(2018, 1, 1)
                age = datetime.date.today().year - birth_date.year - (
                    (datetime.date.today().month, datetime.date.today().day) < (birth_date.month, birth_date.day)
                )
                if age == 6:
                    class_group = 'Abelhinhas Laboriosas'
                elif age == 7:
                    class_group = 'Luminares'
                elif age == 8:
                    class_group = 'Edificadores'
                elif age == 9:
                    class_group = 'Mãos Ajudadoras'
                else:
                    class_group = ''
                child = Child.objects.create(
                    name=name.strip(),
                    birth_date=birth_date,
                    class_group=class_group,
                    active=True,
                )
                GuardianChild.objects.get_or_create(
                    guardian_user=user, child=child, defaults={'relationship': 'Responsável'}
                )

        return user


class UserEditForm(forms.Form):
    ROLE_CHOICES = UserCreateForm.ROLE_CHOICES

    whatsapp_number = forms.CharField(label='WhatsApp', max_length=20, disabled=True)
    first_name = forms.CharField(label='Nome', max_length=150, required=False)
    last_name = forms.CharField(label='Sobrenome', max_length=150, required=False)
    role = forms.ChoiceField(label='Perfil', choices=ROLE_CHOICES)
    extra_roles = forms.MultipleChoiceField(
        label='Perfis adicionais',
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    password = forms.CharField(label='Senha (em branco para manter)', widget=forms.PasswordInput, required=False)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['whatsapp_number'].initial = self.instance.whatsapp_number
            self.fields['first_name'].initial = self.instance.first_name
            self.fields['last_name'].initial = self.instance.last_name
            self.fields['role'].initial = self.instance.role
            current = {self.instance.role}
            group_map_rev = {
                'Diretoria': 'DIRETORIA',
                'Secretaria': 'SECRETARIA',
                'Tesoureiro': 'TESOUREIRO',
                'Professor': 'PROFESSOR',
                'Responsavel': 'RESPONSAVEL',
                'ADM': 'ADM',
            }
            for g in self.instance.groups.all():
                role_value = group_map_rev.get(g.name)
                if role_value:
                    current.add(role_value)
            current.discard(self.instance.role)
            self.fields['extra_roles'].initial = list(current)

    def _assign_group(self, user, role, extras=None):
        extras = extras or []
        group_map = {
            'DIRETORIA': 'Diretoria',
            'SECRETARIA': 'Secretaria',
            'TESOUREIRO': 'Tesoureiro',
            'PROFESSOR': 'Professor',
            'RESPONSAVEL': 'Responsavel',
            'ADM': 'ADM',
        }
        group_names = []
        for r in {role, *extras}:
            g = group_map.get(r)
            if g:
                group_names.append(g)
        groups = [Group.objects.get_or_create(name=g)[0] for g in group_names]
        user.groups.set(groups)

    def save(self):
        user = self.instance
        data = self.cleaned_data
        user.first_name = data.get('first_name')
        user.last_name = data.get('last_name')
        user.role = data['role']
        if data.get('password'):
            user.set_password(data['password'])
        user.save()
        extras = data.get('extra_roles') or []
        self._assign_group(user, data['role'], extras)
        return user
