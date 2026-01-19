from django.urls import path

from . import views

urlpatterns = [
    path('content/', views.content_list, name='curriculum-content'),
    path('content/new/', views.content_create, name='curriculum-content-new'),
    path('content/<int:pk>/edit/', views.content_edit, name='curriculum-content-edit'),
    path('schedule/', views.schedule_list, name='curriculum-schedule'),
    path('schedule/new/', views.schedule_new, name='curriculum-schedule-new'),
    path('progress/', views.progress_mark, name='curriculum-progress'),
    path('progress/child/<int:child_id>/', views.child_progress, name='curriculum-child-progress'),
    path('my/', views.my_progress, name='curriculum-my'),
]
