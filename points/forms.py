from django import forms

from children.models import Child
from .models import PointsLedger


class PointsIndividualForm(forms.ModelForm):
    class Meta:
        model = PointsLedger
        fields = ['child', 'points', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['child'].queryset = Child.objects.filter(active=True).order_by('name')


class PointsBatchForm(forms.Form):
    class_group = forms.ChoiceField(label='Classe', required=False)
    points = forms.IntegerField(label='Pontos')
    reason = forms.CharField(label='Motivo', widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        class_groups = kwargs.pop('class_groups', [])
        super().__init__(*args, **kwargs)
        self.fields['class_group'].choices = [('', 'Todas as classes')] + [(cg, cg) for cg in class_groups]


class PointsExtractForm(forms.Form):
    child = forms.ModelChoiceField(label='Aventureiro', queryset=Child.objects.filter(active=True).order_by('name'))
