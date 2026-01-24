from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from core.mercadopago import create_mercadopago_pix_payment
from core.permissions import role_required
from .forms import ProductForm
from .models import Cart, CartItem, Category, Order, OrderItem, Product


def catalog(request):
    products = list(Product.objects.filter(active=True).select_related('category'))
    for p in products:
        p.opt_list = [o.strip() for o in (p.options or '').split(',') if o.strip()]
    categories = Category.objects.filter(active=True)
    return render(request, 'store/catalog.html', {'products': products, 'categories': categories, 'title': 'Loja'})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    return render(request, 'store/product_detail.html', {'product': product, 'title': product.name})


def _get_open_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user, status=Cart.Status.OPEN)
    return cart


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, active=True)
    cart = _get_open_cart(request.user)
    qty = int(request.POST.get('quantity', 1))
    option = request.POST.get('option', '').strip()
    variant_id = request.POST.get('variant_id')
    variant = None
    if variant_id:
        variant = get_object_or_404(product.variants, pk=variant_id, active=True)
        option = variant.name
        price = variant.price
    else:
        price = product.price
    qty = max(1, qty)
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        option=option,
        variant=variant,
        defaults={'quantity': qty, 'unit_price': price},
    )
    if not created:
        item.quantity += qty
        item.save()
    messages.success(request, f'{product.name} adicionado ao carrinho.')
    return redirect('store-cart')


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user, cart__status=Cart.Status.OPEN)
    item.delete()
    messages.success(request, 'Item removido do carrinho.')
    return redirect('store-cart')


@login_required
def cart_view(request):
    cart = Cart.objects.filter(user=request.user, status=Cart.Status.OPEN).prefetch_related('items__product').first()
    total = cart.total() if cart else 0
    return render(request, 'store/cart.html', {'cart': cart, 'total': total, 'title': 'Carrinho'})


@login_required
@transaction.atomic
def checkout(request):
    cart = Cart.objects.filter(user=request.user, status=Cart.Status.OPEN).prefetch_related('items__product').first()
    if not cart or cart.items.count() == 0:
        messages.error(request, 'Carrinho vazio.')
        return redirect('store-catalog')
    order = Order.objects.create(user=request.user, cart=cart, total=cart.total(), status=Order.Status.PENDING)
    for item in cart.items.select_related('product'):
        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        # atualiza estoque
        if item.product.stock >= item.quantity:
            item.product.stock -= item.quantity
            item.product.save()
        if item.variant and item.variant.stock >= item.quantity:
            item.variant.stock -= item.quantity
            item.variant.save()
    cart.status = Cart.Status.CHECKED_OUT
    cart.save()
    messages.success(request, f'Pedido {order.id} criado.')
    return redirect('store-orders')


@login_required
def orders(request):
    orders_qs = Order.objects.filter(user=request.user).order_by('-created_at').prefetch_related('items__product')
    return render(request, 'store/orders.html', {'orders': orders_qs, 'title': 'Meus pedidos'})


@login_required
def pay_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if request.method == 'POST':
        order.status = Order.Status.PAID
        order.save(update_fields=['status'])
        messages.success(request, f'Pedido {order.id} marcado como pago.')
        return redirect('store-orders')
    pix_code = f"PIX-ORDER-{order.id}-{int(order.total)}-{order.user.whatsapp_number}"
    mp_payment = create_mercadopago_pix_payment(
        request,
        description=f'Pedido {order.id}',
        amount=order.total,
        external_reference=f'ORDER:{order.id}',
    )
    return render(
        request,
        'store/pix_payment.html',
        {
            'order': order,
            'pix_code': pix_code,
            'mp_payment': mp_payment,
            'title': 'Pagamento PIX',
        },
    )


@role_required([User.Role.DIRETORIA, User.Role.TESOUREIRO])
def manage_products(request):
    products = Product.objects.all().select_related('category')
    return render(request, 'store/manage_products.html', {'products': products, 'title': 'Produtos'})


@role_required([User.Role.DIRETORIA, User.Role.TESOUREIRO])
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        # criar variações
        names = request.POST.getlist('variant_name')
        prices = request.POST.getlist('variant_price')
        stocks = request.POST.getlist('variant_stock')
        parsed_variants = []
        for n, p, s in zip(names, prices, stocks):
            if n and p and s:
                try:
                    parsed_variants.append((n.strip(), float(str(p).replace(',', '.')), int(s)))
                except ValueError:
                    continue
        if parsed_variants:
            product.variants.all().delete()
            for name, price, stock in parsed_variants:
                product.variants.create(name=name, price=price, stock=stock, active=True)
            total_stock = sum(v[2] for v in parsed_variants)
            product.stock = total_stock
            product.price = parsed_variants[0][1]
            product.save(update_fields=['stock', 'price'])
        messages.success(request, 'Produto criado.')
        return redirect('store-manage-products')
    return render(
        request,
        'store/product_form.html',
        {'form': form, 'title': 'Novo produto', 'variant_data': []},
    )


@role_required([User.Role.DIRETORIA, User.Role.TESOUREIRO])
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    initial_variants = '\n'.join([f'{v.name};{v.price};{v.stock}' for v in product.variants.all()])
    form = ProductForm(request.POST or None, instance=product, initial={'variants': initial_variants})
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        names = request.POST.getlist('variant_name')
        prices = request.POST.getlist('variant_price')
        stocks = request.POST.getlist('variant_stock')
        parsed_variants = []
        for n, p, s in zip(names, prices, stocks):
            if n and p and s:
                try:
                    parsed_variants.append((n.strip(), float(str(p).replace(',', '.')), int(s)))
                except ValueError:
                    continue
        if parsed_variants:
            product.variants.all().delete()
            for name, price, stock in parsed_variants:
                product.variants.create(name=name, price=price, stock=stock, active=True)
            total_stock = sum(v[2] for v in parsed_variants)
            product.stock = total_stock
            product.price = parsed_variants[0][1]
            product.save(update_fields=['stock', 'price'])
        messages.success(request, 'Produto atualizado.')
        return redirect('store-manage-products')
    variant_data = [{'name': v.name, 'price': float(v.price), 'stock': v.stock} for v in product.variants.all()]
    return render(
        request,
        'store/product_form.html',
        {'form': form, 'title': 'Editar produto', 'variant_data': variant_data},
    )


@role_required([User.Role.DIRETORIA, User.Role.TESOUREIRO])
def manage_orders(request):
    orders_qs = Order.objects.all().order_by('-created_at').prefetch_related('items__product', 'user')
    return render(request, 'store/manage_orders.html', {'orders': orders_qs, 'title': 'Pedidos da loja'})
