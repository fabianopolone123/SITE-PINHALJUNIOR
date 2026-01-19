from django.urls import path

from . import views
from . import views_discount

urlpatterns = [
    path('fees/', views.fees_list, name='finance-fees'),
    path('fees/new/', views.fee_generate, name='finance-fee-new'),
    path('fees/child/<int:child_id>/', views.child_fees, name='finance-child-fees'),
    path('reports/', views.reports, name='finance-reports'),
    path('my/', views.my_fees, name='finance-my'),
    path('my/<int:child_id>/', views.my_child_fees, name='finance-my-child'),
    path('my/<int:child_id>/fee/<int:fee_id>/pay/', views.fee_payment, name='finance-fee-payment'),
    path('my/<int:child_id>/pay-open/', views.pay_all_open, name='finance-pay-all-open'),
    path('discount/<int:child_id>/', views_discount.apply_discount, name='finance-discount'),
]
