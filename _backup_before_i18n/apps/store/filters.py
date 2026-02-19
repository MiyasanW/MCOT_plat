from django.db.models import Q
import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    q = django_filters.CharFilter(method='filter_search')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['category', 'price', 'is_active']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | 
            Q(description__icontains=value)
        )
