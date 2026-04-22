from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row, Submit
from django import forms
from django.utils.translation import gettext_lazy as _lazy

from .models import OpportunityAttachment, OpportunityCollaborator, TrackedOpportunity


class TrackedOpportunityForm(forms.ModelForm):
    """Form for updating a tracked opportunity's status, priority, and notes."""

    class Meta:
        model = TrackedOpportunity
        fields = ['status', 'priority', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                _lazy('Tracking Details'),
                Row(
                    Column('status', css_class='col-md-6'),
                    Column('priority', css_class='col-md-6'),
                ),
                'notes',
            ),
            Div(
                Submit('submit', _lazy('Update Tracking'), css_class='btn btn-primary me-2'),
                css_class='mt-3',
            ),
        )


class CollaboratorForm(forms.Form):
    """Form for adding an internal or external collaborator."""

    COLLABORATOR_TYPE_CHOICES = [
        ('internal', _lazy('Internal User')),
        ('external', _lazy('External Collaborator')),
    ]

    collaborator_type = forms.ChoiceField(
        choices=COLLABORATOR_TYPE_CHOICES,
        label=_lazy('Collaborator Type'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    username = forms.CharField(
        required=False, label=_lazy('Username'),
        help_text=_lazy('Bounty username for internal collaborators.'),
    )
    email = forms.EmailField(
        required=False, label=_lazy('Email'),
        help_text=_lazy('Email address for external collaborators.'),
    )
    name = forms.CharField(
        required=False, label=_lazy('Name'),
        help_text=_lazy('Full name for external collaborators.'),
    )
    role = forms.ChoiceField(
        choices=OpportunityCollaborator.Role.choices,
        label=_lazy('Role'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'collaborator_type', 'username', 'email', 'name', 'role',
            Div(
                Submit('submit', _lazy('Add Collaborator'), css_class='btn btn-primary btn-sm'),
                css_class='mt-3',
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        collab_type = cleaned_data.get('collaborator_type')
        username = cleaned_data.get('username', '').strip()
        email = cleaned_data.get('email', '').strip()

        if collab_type == 'internal' and not username:
            self.add_error('username', _lazy('Username is required for internal collaborators.'))
        elif collab_type == 'external' and not email:
            self.add_error('email', _lazy('Email is required for external collaborators.'))

        return cleaned_data


class LocalSignForm(forms.Form):
    """Upload a locally-signed approval PDF when Manifest isn't deployed."""

    signed_pdf = forms.FileField(
        label=_lazy('Signed approval PDF'),
        help_text=_lazy('Upload the signed internal approval document.'),
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
    )

    def clean_signed_pdf(self):
        f = self.cleaned_data['signed_pdf']
        if not f.name.lower().endswith('.pdf'):
            raise forms.ValidationError(_lazy('Only PDF files are accepted.'))
        return f


class AttachmentForm(forms.ModelForm):
    """Upload a diligence document to a tracked opportunity."""

    class Meta:
        model = OpportunityAttachment
        fields = ['file', 'description', 'visibility']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': _lazy('Optional — what is this file?'),
            }),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
            'visibility': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }
