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
from django.urls import path, include
from .admin_site import MCOTAdminSite

# Swap the class of the default admin.site so both
# dashboard and sidebar use our custom ordering.
admin.site.__class__ = MCOTAdminSite

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Login/Signup + Google (ต้องอยู่ก่อน auth)
    path('accounts/', include('django.contrib.auth.urls')),  # password_reset, password_change ฯลฯ
    path('summernote/', include('django_summernote.urls')),
    path('', include('apps.store.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
