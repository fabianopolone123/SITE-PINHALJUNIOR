from django.urls import path

from . import views

urlpatterns = [
    path('overview/', views.overview, name='documents-overview'),
    path('child/<int:child_id>/', views.child_detail, name='documents-child'),
    path('child/<int:child_id>/update/<int:doc_id>/', views.child_doc_update, name='documents-child-update'),
    path('child/<int:child_id>/upload/<int:doc_id>/', views.child_doc_upload, name='documents-child-upload'),
    path('request/<int:child_id>/<int:doctype_id>/', views.send_request, name='documents-request'),
    path('my/', views.my_documents, name='documents-my'),
]
