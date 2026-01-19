from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='points-index'),
    path('child/<int:child_id>/', views.child_statement, name='points-child'),
    path('add/individual/', views.add_individual, name='points-add-individual'),
    path('add/batch/', views.add_batch, name='points-add-batch'),
    path('my/', views.my_points, name='points-my'),
    path('extract/', views.extract, name='points-extract'),
]
