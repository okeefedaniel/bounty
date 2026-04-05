from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _lazy

from .models import BountyProfile

User = get_user_model()


class LoginForm(AuthenticationForm):
    """Styled login form."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _lazy('Username'),
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _lazy('Password'),
        }),
    )


class ProfileForm(forms.ModelForm):
    organization_name = forms.CharField(max_length=255, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'title', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            from .models import get_bounty_profile
            profile = get_bounty_profile(self.instance)
            self.fields['organization_name'].initial = profile.organization_name

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            from .models import get_bounty_profile
            profile = get_bounty_profile(user)
            profile.organization_name = self.cleaned_data.get('organization_name', '')
            profile.save(update_fields=['organization_name'])
        return user
