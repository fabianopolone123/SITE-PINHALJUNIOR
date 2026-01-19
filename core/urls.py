from django.urls import path

from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/diretoria/', views.dashboard_diretoria, name='dashboard-diretoria'),
    path('dashboard/secretaria/', views.dashboard_secretaria, name='dashboard-secretaria'),
    path('dashboard/tesoureiro/', views.dashboard_tesoureiro, name='dashboard-tesoureiro'),
    path('dashboard/professor/', views.dashboard_professor, name='dashboard-professor'),
    path('dashboard/responsavel/', views.dashboard_responsavel, name='dashboard-responsavel'),
    path('config/', views.config_view, name='config'),
    path('relatorios-diretoria/', views.director_reports, name='director-reports'),
    path('usuarios/novo/', views.user_create, name='user-create'),
    path('usuarios/', views.user_list, name='user-list'),
    path('usuarios/<int:pk>/ativar/', views.user_activate, name='user-activate'),
    path('usuarios/<int:pk>/editar/', views.user_edit, name='user-edit'),
    path('usuarios/aventureiro/<int:pk>/detalhe/', views.child_overview, name='child-overview'),
    path('usuarios/aventureiro/<int:pk>/editar/', views.child_edit, name='child-edit'),
    path('sair/', views.logout_view, name='logout'),
    path('trocar-perfil/<str:role>/', views.switch_role, name='switch-role'),
    path('cadastro/', views.signup, name='signup'),
]
