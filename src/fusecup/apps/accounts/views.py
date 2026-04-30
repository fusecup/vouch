from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from .forms import AccountSettingsForm


class AccountSettings(LoginRequiredMixin, FormView):
    template_name = "account/settings.html"
    form_class = AccountSettingsForm
    success_url = reverse_lazy("account_settings")

    def get_initial(self):
        user = self.request.user
        initial_vals = {
            # 'show_in_points': user.show_in_points,
            "first_name": user.first_name,  # type: ignore[reportAttributeAccessIssue]
            "last_name": user.last_name,  # type: ignore[reportAttributeAccessIssue]
        }
        return initial_vals

    def form_valid(self, form):
        form.update_data(self.request)
        return super().form_valid(form)


account_settings = AccountSettings.as_view()
