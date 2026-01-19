from django.conf import settings
from django.db import models
from django.utils import timezone


class Child(models.Model):
    name = models.CharField('Nome', max_length=150)
    birth_date = models.DateField('Data de nascimento')
    class_group = models.CharField('Turma/Unidade', max_length=80, blank=True)
    active = models.BooleanField('Ativo', default=True)
    fee_discount_percent = models.DecimalField('Desconto %', max_digits=5, decimal_places=2, default=0)
    fee_discount_amount = models.DecimalField('Desconto valor', max_digits=10, decimal_places=2, default=0)
    gender = models.CharField('Sexo', max_length=10, blank=True)
    cpf = models.CharField('CPF', max_length=20, blank=True)
    birth_certificate_number = models.CharField('Certidão de nascimento', max_length=60, blank=True)
    father_name = models.CharField('Nome do pai', max_length=150, blank=True)
    father_cpf = models.CharField('CPF do pai', max_length=20, blank=True)
    father_phone = models.CharField('Telefone do pai', max_length=30, blank=True)
    father_absent = models.BooleanField('Pai ausente/desconhecido', default=False)
    mother_name = models.CharField('Nome da mãe', max_length=150, blank=True)
    mother_cpf = models.CharField('CPF da mãe', max_length=20, blank=True)
    mother_phone = models.CharField('Telefone da mãe', max_length=30, blank=True)
    mother_absent = models.BooleanField('Mãe ausente/desconhecida', default=False)

    def __str__(self):
        return self.name


class GuardianChild(models.Model):
    guardian_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='guardian_links',
        verbose_name='Responsável',
    )
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='guardian_links', verbose_name='Aventureiro')
    relationship = models.CharField('Vínculo', max_length=50, blank=True)

    class Meta:
        unique_together = ('guardian_user', 'child')
        verbose_name = 'Vínculo Responsável'
        verbose_name_plural = 'Vínculos Responsáveis'

    def __str__(self):
        return f'{self.guardian_user} -> {self.child}'


class ChildFace(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='faces', verbose_name='Aventureiro')
    image = models.ImageField(upload_to='child_faces/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Rosto do Aventureiro'
        verbose_name_plural = 'Rostos do Aventureiro'

    def __str__(self):
        return f'Face de {self.child}'


class ChildHealth(models.Model):
    child = models.OneToOneField(Child, on_delete=models.CASCADE, related_name='health')
    allergies = models.TextField('Alergias', blank=True)
    medications = models.TextField('Medicamentos de uso contínuo', blank=True)
    restrictions = models.TextField('Restrições médicas', blank=True)
    observations = models.TextField('Observações', blank=True)
    emergency_contact = models.CharField('Contato de emergência', max_length=150, blank=True)
    emergency_phone = models.CharField('Telefone de emergência', max_length=30, blank=True)
    health_plan = models.CharField('Plano de saúde', max_length=120, blank=True)
    auth_activity = models.BooleanField('Autoriza atividades', default=False)
    auth_medical = models.BooleanField('Autoriza atendimento médico', default=False)
    auth_rules = models.BooleanField('Aceita regulamento', default=False)

    def __str__(self):
        return f'Saúde de {self.child}'
