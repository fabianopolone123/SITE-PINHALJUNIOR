from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['whatsapp_number']
    list_display = ('whatsapp_number', 'role', 'first_name', 'last_name', 'is_active', 'is_staff')
    search_fields = ('whatsapp_number', 'first_name', 'last_name', 'email')
    list_filter = ('role', 'is_active', 'is_staff')
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    fieldsets = (
        (None, {'fields': ('whatsapp_number', 'password')}),
        (_('Informações pessoais'), {'fields': ('first_name', 'last_name', 'email', 'photo', 'role')}),
        (_('Permissões'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Datas importantes'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('whatsapp_number', 'role', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_active'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')
