from django import forms

from .models import Child, GuardianChild

RELATIONSHIP_CHOICES = [
    ('Pai/Mãe', 'Pai/Mãe'),
    ('Responsável', 'Responsável'),
    ('Avô/Avó', 'Avô/Avó'),
    ('Tio/Tia', 'Tio/Tia'),
    ('Irmão/Irmã', 'Irmão/Irmã'),
]


class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['name', 'birth_date', 'class_group', 'active']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        class_choices = [
            ('Abelhinhas Laboriosas', 'Abelhinhas Laboriosas'),
            ('Luminares', 'Luminares'),
            ('Edificadores', 'Edificadores'),
            ('Mãos Ajudadoras', 'Mãos Ajudadoras'),
        ]
        self.fields['class_group'] = forms.ChoiceField(
            choices=class_choices, required=False, label='Classe'
        )


class GuardianChildForm(forms.ModelForm):
    relationship = forms.ChoiceField(choices=RELATIONSHIP_CHOICES, required=False, label='Vínculo')

    class Meta:
        model = GuardianChild
        fields = ['guardian_user', 'child', 'relationship']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User

        self.fields['guardian_user'].queryset = User.objects.filter(role=User.Role.RESPONSAVEL)
        self.fields['guardian_user'].label = 'Responsável'
        self.fields['child'].label = 'Aventureiro'
