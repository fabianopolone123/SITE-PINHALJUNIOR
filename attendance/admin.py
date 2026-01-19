from django.contrib import admin

from .models import AttendanceRecord, AttendanceSession


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('date', 'type', 'class_group', 'created_by_user')
    list_filter = ('type', 'class_group', 'date')
    search_fields = ('class_group',)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('session', 'child', 'present', 'marked_by_user', 'marked_at')
    list_filter = ('present', 'session__type', 'session__class_group', 'session__date')
    search_fields = ('child__name', 'session__class_group')
