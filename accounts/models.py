from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .utils import normalize_whatsapp_number


class UserManager(BaseUserManager):
    def _create_user(self, whatsapp_number: str, password: str | None, **extra_fields):
        if not whatsapp_number:
            raise ValueError('O número de WhatsApp é obrigatório.')
        if not password:
            raise ValueError('A senha é obrigatória.')

        normalized = normalize_whatsapp_number(whatsapp_number)
        if not normalized:
            raise ValueError('Número de WhatsApp inválido ou não pôde ser normalizado.')

        user = self.model(whatsapp_number=normalized, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, whatsapp_number: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', User.Role.RESPONSAVEL)
        return self._create_user(whatsapp_number, password, **extra_fields)

    def create_superuser(self, whatsapp_number: str, password: str | None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADM)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuário precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuário precisa ter is_superuser=True.')

        return self._create_user(whatsapp_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADM = 'ADM', 'ADM'
        DIRETORIA = 'DIRETORIA', 'Diretoria'
        SECRETARIA = 'SECRETARIA', 'Secretaria'
        TESOUREIRO = 'TESOUREIRO', 'Tesoureiro'
        PROFESSOR = 'PROFESSOR', 'Professor'
        RESPONSAVEL = 'RESPONSAVEL', 'Responsável'

    whatsapp_number = models.CharField('WhatsApp', max_length=20, unique=True)
    financial_whatsapp = models.CharField('WhatsApp financeiro', max_length=20, blank=True)
    financial_phone = models.CharField('Telefone financeiro', max_length=20, blank=True)
    address = models.CharField('Endereço', max_length=255, blank=True)
    role = models.CharField('Função', max_length=20, choices=Role.choices, default=Role.RESPONSAVEL)
    first_name = models.CharField('Nome', max_length=150, blank=True)
    last_name = models.CharField('Sobrenome', max_length=150, blank=True)
    email = models.EmailField('E-mail', blank=True)
    photo = models.ImageField('Foto 3x4', upload_to='user_photos/', blank=True, null=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'whatsapp_number'
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def save(self, *args, **kwargs):
        if self.whatsapp_number:
            self.whatsapp_number = normalize_whatsapp_number(self.whatsapp_number)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.whatsapp_number

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
