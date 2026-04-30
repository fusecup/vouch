from django import template

register = template.Library()


@register.filter(name="field_type")
def field_type(field):
    return field.field.widget.__class__.__name__


@register.filter(name="to_list")
def to_list(field):
    if isinstance(field, list):
        return field
    else:
        return [field]
