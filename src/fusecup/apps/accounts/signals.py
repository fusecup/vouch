from django.contrib.auth.signals import user_logged_in


def set_user_timezone(sender, user, request, **kwargs):
    detected_tz = request.session.get("detected_tz", None)
    if detected_tz:
        user.timezone = detected_tz
        user.save()


user_logged_in.connect(set_user_timezone)
