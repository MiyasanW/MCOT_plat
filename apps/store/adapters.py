from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from apps.store.models import Profile


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for allauth social login.
    Forces new Google users to complete their profile (phone number).
    """

    def save_user(self, request, sociallogin, form=None):
        """Create a Profile when a new user signs up via Google."""
        user = super().save_user(request, sociallogin, form)
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
