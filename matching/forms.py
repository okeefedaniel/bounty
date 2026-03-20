from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Field, Fieldset, HTML, Layout, Row, Submit
from django import forms
from django.utils.translation import gettext_lazy as _lazy

from .models import FocusArea, MatchPreference, StatePreference


class MatchPreferenceForm(forms.ModelForm):
    """Form for editing AI grant-matching preferences."""

    focus_areas = forms.MultipleChoiceField(
        choices=FocusArea.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_lazy('Focus Areas'),
    )

    keywords = forms.CharField(
        required=False,
        label=_lazy('Keywords'),
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. climate, broadband, opioid, workforce training',
        }),
        help_text=_lazy('Comma-separated keywords describing your interests'),
    )

    class Meta:
        model = MatchPreference
        fields = ['focus_areas', 'keywords', 'funding_range_min', 'funding_range_max', 'description', 'digest_frequency', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe your priorities, mission, or what you are looking for...',
            }),
        }
        labels = {
            'funding_range_min': _lazy('Minimum Funding Amount'),
            'funding_range_max': _lazy('Maximum Funding Amount'),
            'description': _lazy('Additional Context'),
            'digest_frequency': _lazy('Digest Emails'),
            'is_active': _lazy('Enable AI Matching'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert JSON list to comma-separated string for display
        if self.instance and self.instance.keywords:
            self.initial['keywords'] = ', '.join(self.instance.keywords)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        select_all = (
            '<a href="#" class="select-all-toggle small text-primary text-decoration-none" '
            'data-select-all="Select All" data-deselect-all="Deselect All">Select All</a>'
        )
        self.helper.layout = Layout(
            Fieldset(_lazy('Areas of Interest'), HTML(select_all), 'focus_areas'),
            Fieldset(_lazy('Keywords'), 'keywords'),
            Fieldset(
                _lazy('Funding Range'),
                Row(
                    Column('funding_range_min', css_class='col-md-6'),
                    Column('funding_range_max', css_class='col-md-6'),
                ),
            ),
            Fieldset(_lazy('Additional Context'), 'description'),
            Fieldset(
                _lazy('Notifications'),
                'digest_frequency',
                HTML('<p class="text-muted small mb-0">Receive a summary of new matches by email on your chosen schedule.</p>'),
            ),
            Field('is_active'),
            Div(Submit('submit', _lazy('Save Preferences'), css_class='btn btn-primary me-2'), css_class='mt-4'),
        )

    def clean_keywords(self):
        raw = self.cleaned_data.get('keywords', '')
        if not raw:
            return []
        return [kw.strip() for kw in raw.split(',') if kw.strip()]


class StatePreferenceForm(forms.ModelForm):
    """Form for editing state-wide matching preferences (admin/coordinator only)."""

    focus_areas = forms.MultipleChoiceField(
        choices=FocusArea.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_lazy('State Focus Areas'),
    )

    keywords = forms.CharField(
        required=False,
        label=_lazy('State Keywords'),
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. infrastructure, public health, education equity',
        }),
        help_text=_lazy('Comma-separated keywords describing state-wide priorities'),
    )

    class Meta:
        model = StatePreference
        fields = ['name', 'focus_areas', 'keywords', 'funding_range_min', 'funding_range_max', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describe the state\'s overall funding priorities and mission...',
            }),
        }
        labels = {
            'name': _lazy('Profile Name'),
            'funding_range_min': _lazy('Minimum Funding Amount'),
            'funding_range_max': _lazy('Maximum Funding Amount'),
            'description': _lazy('State Priorities Description'),
            'is_active': _lazy('Active'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.keywords:
            self.initial['keywords'] = ', '.join(self.instance.keywords)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        select_all = (
            '<a href="#" class="select-all-toggle small text-primary text-decoration-none" '
            'data-select-all="Select All" data-deselect-all="Deselect All">Select All</a>'
        )
        self.helper.layout = Layout(
            Fieldset(_lazy('Profile'), 'name'),
            Fieldset(_lazy('State Focus Areas'), HTML(select_all), 'focus_areas'),
            Fieldset(_lazy('State Keywords'), 'keywords'),
            Fieldset(
                _lazy('Funding Range'),
                Row(
                    Column('funding_range_min', css_class='col-md-6'),
                    Column('funding_range_max', css_class='col-md-6'),
                ),
            ),
            Fieldset(_lazy('State Priorities'), 'description'),
            Field('is_active'),
            Div(Submit('submit', _lazy('Save State Preferences'), css_class='btn btn-primary me-2'), css_class='mt-4'),
        )

    def clean_keywords(self):
        raw = self.cleaned_data.get('keywords', '')
        if not raw:
            return []
        return [kw.strip() for kw in raw.split(',') if kw.strip()]
