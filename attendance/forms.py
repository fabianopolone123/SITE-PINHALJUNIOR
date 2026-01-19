from django import forms

from children.models import Child
from .models import AttendanceSession


class AttendanceSessionForm(forms.ModelForm):
    class_group = forms.ChoiceField(label='Turma/Unidade', required=False)

    class Meta:
        model = AttendanceSession
        fields = ['date', 'type', 'class_group']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        groups = (
            Child.objects.filter(active=True)
            .exclude(class_group='')
            .values_list('class_group', flat=True)
            .distinct()
            .order_by('class_group')
        )
        choices = [('', 'Todas as turmas')] + [(g, g) for g in groups]
        self.fields['class_group'].choices = choices
