# from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View


class WelcomeView(View):
    template_name = "welcome.html"

    def get(self, request):
        return render(request, self.template_name)


welcome = WelcomeView.as_view()


class DesignSystemView(View):
    template_name = "design_system.html"

    def get(self, request):
        return render(request, self.template_name)


design_system = DesignSystemView.as_view()
