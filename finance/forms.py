from django import forms

from children.models import Child
from .models import Fee


class FeeGenerationForm(forms.Form):
    reference_month = forms.CharField(label='Mês (YYYY-MM)', max_length=7)
    amount = forms.DecimalField(label='Valor', max_digits=10, decimal_places=2)
    due_date = forms.DateField(label='Vencimento', widget=forms.DateInput(attrs={'type': 'date'}))
    class_group = forms.CharField(label='Classe (opcional)', required=False)
    child = forms.ModelChoiceField(queryset=Child.objects.none(), required=False, label='Criança (opcional)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['child'].queryset = Child.objects.filter(active=True).order_by('name')

    def clean(self):
        cleaned = super().clean()
        cg = cleaned.get('class_group')
        child = cleaned.get('child')
        if not cg and not child:
            raise forms.ValidationError('Informe uma turma ou uma criança.')
        return cleaned


class FeeFilterForm(forms.Form):
    reference_month = forms.CharField(label='Mês (YYYY-MM)', max_length=7, required=False)
    status = forms.ChoiceField(choices=[('', 'Todos')] + list(Fee.Status.choices), required=False)
    class_group = forms.CharField(label='Classe', required=False)
