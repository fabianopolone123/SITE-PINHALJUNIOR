from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    variants = forms.CharField(
        label='Variações (uma por linha: Nome;preço;estoque)',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'active', 'category', 'image_url', 'options']
