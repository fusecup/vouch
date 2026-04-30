from django import forms
from django.contrib import messages

from .models import User


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
        ]

    def update_data(self, request):
        user = request.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()
        messages.success(request, "Your settings are updated.")
