from django.contrib.admin import site
from django.utils.translation import gettext_lazy as _

site.site_title = _("fusecup | Administration")
site.site_header = _("fusecup \U00002615")
site.index_title = _("fusecup | Administration")

admin_site = site
