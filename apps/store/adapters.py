from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from apps.store.models import Profile


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for allauth social login.
    Forces new Google users to complete their profile (name + phone).
    """

    def get_signup_form_initial_data(self, sociallogin):
        """Prefill ชื่อ นามสกุล from Google (given_name, family_name)."""
        data = super().get_signup_form_initial_data(sociallogin)
        extra = (sociallogin.account.extra_data or {}) if sociallogin.account else {}
        data.setdefault('first_name', extra.get('given_name', ''))
        data.setdefault('last_name', extra.get('family_name', ''))
        return data

    def save_user(self, request, sociallogin, form=None):
        """Create a Profile when a new user signs up via Google; set first_name, last_name, phone from form."""
        user = super().save_user(request, sociallogin, form)
        if form and hasattr(form, 'cleaned_data'):
            data = form.cleaned_data
            user.first_name = (data.get('first_name') or '').strip()
            user.last_name = (data.get('last_name') or '').strip()
            user.save(update_fields=['first_name', 'last_name'])
            phone = (data.get('phone') or '').strip()
            if phone:
                Profile.objects.update_or_create(user=user, defaults={'phone': phone})
            else:
                Profile.objects.get_or_create(user=user)
        else:
            Profile.objects.get_or_create(user=user)
        return user

    def get_login_redirect_url(self, request):
        """
        Force first-time Google users to the complete-profile page.
        """
        if request.user.is_authenticated:
            try:
                profile = Profile.objects.get(user=request.user)
                if not profile.phone:
                    return '/complete-profile/'
            except Profile.DoesNotExist:
                return '/complete-profile/'
        return super().get_login_redirect_url(request)
