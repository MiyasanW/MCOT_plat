from django.shortcuts import render, redirect
from django.urls import resolve

class SplashScreenMiddleware:
    """
    Middleware to show a splash screen (e.g., Royal Condolence) once per session.
    It intercepts the first request to the site and renders the splash template.
    Once the user clicks 'Enter Site', it sets a session variable and won't show again.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow static files and media to load normally
        if request.path.startswith('/static/') or request.path.startswith('/media/') or request.path.startswith('/admin/'):
            return self.get_response(request)

        # Check if the user is explicitly entering the site from the splash screen
        if request.GET.get('enter') == '1':
            request.session['has_seen_splash'] = True
            # Redirect to the same path but without the query parameters to clean the URL
            return redirect(request.path)

        # Check if they have seen the splash screen in this session
        has_seen_splash = request.session.get('has_seen_splash', False)
        
        # If not, check if SplashConfig is active
        if not has_seen_splash:
            from apps.store.models import SplashConfig
            config = SplashConfig.objects.filter(is_active=True).first()
            if config:
                context = {
                    'message_title': config.title,
                    'message_body': config.message,
                    'splash_image_url': config.image.url if config.image else None,
                }
                return render(request, 'splash.html', context)
            else:
                # If no active config, consider it "seen" so we don't keep checking the DB
                request.session['has_seen_splash'] = True

        # Otherwise, proceed normally
        response = self.get_response(request)
        return response
