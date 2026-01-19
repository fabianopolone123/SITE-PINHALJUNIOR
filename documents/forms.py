from django import forms

from .models import ChildDocument, DocumentFile


class ChildDocumentUpdateForm(forms.ModelForm):
    class Meta:
        model = ChildDocument
        fields = ['status', 'received_date', 'valid_until', 'note']
        widgets = {
            'received_date': forms.DateInput(attrs={'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('status')
        note = cleaned.get('note', '').strip()
        if status == ChildDocument.Status.REJEITADO and not note:
            self.add_error('note', 'Observação é obrigatória ao rejeitar.')
        return cleaned


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = DocumentFile
        fields = ['file']
