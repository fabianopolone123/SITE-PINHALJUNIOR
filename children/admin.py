from django.contrib import admin

from .models import Child, ChildFace, GuardianChild


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_group', 'birth_date', 'active')
    list_filter = ('class_group', 'active')
    search_fields = ('name', 'class_group')


@admin.register(GuardianChild)
class GuardianChildAdmin(admin.ModelAdmin):
    list_display = ('child', 'guardian_user', 'relationship')
    search_fields = ('child__name', 'guardian_user__whatsapp_number', 'relationship')


@admin.register(ChildFace)
class ChildFaceAdmin(admin.ModelAdmin):
    list_display = ('child', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('child__name',)
