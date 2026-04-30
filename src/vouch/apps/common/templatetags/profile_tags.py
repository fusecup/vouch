from django import template
from django.urls import reverse_lazy

register = template.Library()


@register.simple_tag
def active(request, pattern):
    path = request.path
    pattern_path = reverse_lazy(pattern)
    if path == pattern_path:
        return "active"
    return ""
