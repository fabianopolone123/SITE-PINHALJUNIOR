from django.urls import path

from . import views

urlpatterns = [
    path('sessions/', views.session_list, name='attendance-sessions'),
    path('sessions/new', views.session_create, name='attendance-session-new'),
    path('sessions/<int:pk>/take', views.take_attendance, name='attendance-take'),
    path('my/', views.my_attendance, name='attendance-my'),
]
