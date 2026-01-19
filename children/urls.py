from django.urls import path

from . import views

urlpatterns = [
    path('', views.child_list, name='children-list'),
    path('novo/', views.child_create, name='children-create'),
    path('<int:pk>/editar/', views.child_edit, name='children-edit'),
    path('vinculos/', views.vinculos_list, name='children-vinculos'),
    path('meus-aventureiros/', views.meus_aventureiros, name='children-meus'),
    path('meus-aventureiros/adicionar/', views.add_aventureiro, name='children-add'),
]
