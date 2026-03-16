from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Studio, Package


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return ['store:home', 'store:catalog', 'store:studio_list',
                'store:service_list', 'store:contact', 'store:terms']

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return Product.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('store:product_detail', args=[obj.pk])

    def lastmod(self, obj):
        return obj.created_at


class StudioSitemap(Sitemap):
    priority = 0.7
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        return Studio.objects.all()

    def location(self, obj):
        return reverse('store:studio_detail', args=[obj.pk])


class PackageSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        return Package.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('store:package_detail', args=[obj.pk])
