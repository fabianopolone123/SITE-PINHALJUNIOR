from django import forms

from children.models import Child
from .models import ChildProgress, ClassSchedule, ContentItem


class ContentItemForm(forms.ModelForm):
    class Meta:
        model = ContentItem
        fields = ['title', 'description', 'order', 'module', 'active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class ClassScheduleForm(forms.ModelForm):
    class Meta:
        model = ClassSchedule
        fields = ['class_group', 'content_item', 'planned_date', 'status']
        widgets = {'planned_date': forms.DateInput(attrs={'type': 'date'})}


class ProgressMarkForm(forms.Form):
    status = forms.ChoiceField(choices=ChildProgress.Status.choices)
    note = forms.CharField(required=False)


class ProgressSelectionForm(forms.Form):
    class_group = forms.ChoiceField(label='Turma/Unidade')
    content_item = forms.ModelChoiceField(queryset=ContentItem.objects.none(), label='Conteúdo')

    def __init__(self, *args, **kwargs):
        class_groups = kwargs.pop('class_groups', [])
        super().__init__(*args, **kwargs)
        self.fields['class_group'].choices = [(cg, cg) for cg in class_groups]
        self.fields['content_item'].queryset = ContentItem.objects.filter(active=True).order_by('order')
