from django.contrib import admin

from .models import ChildProgress, ClassSchedule, ContentItem


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'module', 'active')
    list_filter = ('module', 'active')
    search_fields = ('title', 'module')


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ('class_group', 'content_item', 'planned_date', 'status', 'created_by_user')
    list_filter = ('class_group', 'status', 'planned_date')
    search_fields = ('class_group', 'content_item__title')


@admin.register(ChildProgress)
class ChildProgressAdmin(admin.ModelAdmin):
    list_display = ('child', 'content_item', 'status', 'marked_by_user', 'marked_at')
    list_filter = ('status', 'content_item__module', 'child__class_group')
    search_fields = ('child__name', 'content_item__title', 'note')
