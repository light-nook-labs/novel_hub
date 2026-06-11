from django.apps import AppConfig
from django.conf import settings


class SiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "novels"

    def ready(self):
        self.verbose_name = settings.TOML.get("site", {}).get("name", "Novel Hub")
