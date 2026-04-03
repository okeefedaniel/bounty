from django import forms
from django.contrib.auth import get_user_model

from .models import BountyProfile

User = get_user_model()


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
