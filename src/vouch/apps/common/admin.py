from django.contrib.admin import site
from django.utils.translation import gettext_lazy as _

site.site_title = _("vouch | Administration")
site.site_header = _("vouch \U00002615")
site.index_title = _("vouch | Administration")

admin_site = site
