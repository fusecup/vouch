from django.conf import settings
from django.urls import include, path
from django.views.generic import TemplateView

from common.admin import admin_site
from fc_uikit.views import design_system, welcome

robots_txt = TemplateView.as_view(template_name="robots.txt", content_type="text/plain")

urlpatterns = [
    path("tz_detect/", include("tz_detect.urls")),
    path("a/", include("allauth.urls")),
    path("admin/", admin_site.urls),
    path("", welcome, name="welcome"),
    path("design-system/", design_system, name="design_system"),
    path("d/", include("activity.urls")),
    path("robots.txt", robots_txt, name="robots_txt"),
]
if settings.DEBUG:
    # Local Media
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    import debug_toolbar  # pyright: ignore[reportMissingTypeStubs]

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
