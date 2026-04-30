from typing import override

from allauth.account.adapter import DefaultAccountAdapter  # type: ignore[reportMissingTypeStubs]
from django.http import HttpRequest


class SignupAccountAdapter(DefaultAccountAdapter):
    @override
    def is_open_for_signup(self, request: HttpRequest) -> bool:  # type: ignore[reportIncompatibleMethodOverride]
        return True
