from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Field, Fieldset, HTML, Layout, Row, Submit
from django import forms
from django.utils.translation import gettext_lazy as _lazy

from .models import MatchPreference


class MatchPreferenceForm(forms.ModelForm):
    """Form for editing AI grant-matching preferences."""

    focus_areas = forms.MultipleChoiceField(
        choices=MatchPreference.FocusArea.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_lazy('Focus Areas'),
    )

    class Meta:
        model = MatchPreference
        fields = ['focus_areas', 'funding_range_min', 'funding_range_max', 'description', 'is_active']
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
            'is_active': _lazy('Enable AI Matching'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        select_all = (
            '<a href="#" class="select-all-toggle small text-primary text-decoration-none" '
            'data-select-all="Select All" data-deselect-all="Deselect All">Select All</a>'
        )
        self.helper.layout = Layout(
            Fieldset(_lazy('Areas of Interest'), HTML(select_all), 'focus_areas'),
            Fieldset(
                _lazy('Funding Range'),
                Row(
                    Column('funding_range_min', css_class='col-md-6'),
                    Column('funding_range_max', css_class='col-md-6'),
                ),
            ),
            Fieldset(_lazy('Additional Context'), 'description'),
            Field('is_active'),
            Div(Submit('submit', _lazy('Save Preferences'), css_class='btn btn-primary me-2'), css_class='mt-4'),
        )
