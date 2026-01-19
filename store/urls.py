from django.urls import path

from . import views

urlpatterns = [
    path('', views.catalog, name='store-catalog'),
    path('produto/<int:pk>/', views.product_detail, name='store-product'),
    path('carrinho/', views.cart_view, name='store-cart'),
    path('carrinho/adicionar/<int:product_id>/', views.add_to_cart, name='store-add-to-cart'),
    path('carrinho/remover/<int:item_id>/', views.remove_from_cart, name='store-remove-item'),
    path('checkout/', views.checkout, name='store-checkout'),
    path('pedidos/', views.orders, name='store-orders'),
    path('pedidos/<int:order_id>/pagamento/', views.pay_order, name='store-pay-order'),

    path('gestao/produtos/', views.manage_products, name='store-manage-products'),
    path('gestao/produtos/novo/', views.product_create, name='store-product-create'),
    path('gestao/produtos/<int:pk>/editar/', views.product_edit, name='store-product-edit'),
    path('gestao/pedidos/', views.manage_orders, name='store-manage-orders'),
]
