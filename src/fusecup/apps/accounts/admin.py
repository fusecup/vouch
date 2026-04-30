from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from import_export.admin import ExportMixin

from accounts.models import User

from .export_resources import UserResource


class UserAdmin(ExportMixin, BaseUserAdmin):
    resource_classes = [UserResource]
    model: Any = User
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "timezone",
        "date_joined",
        "last_login",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
    )
    search_fields = ("first_name", "last_name", "email")
    ordering = ("email",)
    readonly_fields = ("date_joined", "last_login")

    form = UserChangeForm
    add_form = UserCreationForm

    fieldsets = (
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "timezone",
                    "password",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    # add_fieldsets is a non standard UserAdmin setting, used by add_form.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                ),
            },
        ),
    )

    def get_inline_instances(self, request, obj=None):
        """Overridden to prevent showing of UserProfile inline in add_form."""
        if obj is None:
            # When obj==None, it means it was called from self.add_view().
            return []
        return super(UserAdmin, self).get_inline_instances(request, obj=obj)


admin.site.register(User, UserAdmin)
