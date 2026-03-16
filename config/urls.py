"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import TemplateView
from .admin_site import MCOTAdminSite
from apps.store.sitemaps import StaticViewSitemap, ProductSitemap, StudioSitemap, PackageSitemap

# Swap the class of the default admin.site so both
# dashboard and sidebar use our custom ordering.
admin.site.__class__ = MCOTAdminSite

sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
    'studios': StudioSitemap,
    'packages': PackageSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Login/Signup + Google (ต้องอยู่ก่อน auth)
    path('accounts/', include('django.contrib.auth.urls')),  # password_reset, password_change ฯลฯ
    path('summernote/', include('django_summernote.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('', include('apps.store.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
