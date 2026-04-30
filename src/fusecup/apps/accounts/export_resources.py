from django.contrib.auth import get_user_model
from import_export.resources import ModelResource

User = get_user_model()


class UserResource(ModelResource):
    class Meta:
        model = User
        exclude = ("password",)
