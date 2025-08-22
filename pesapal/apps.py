from django.apps import AppConfig


class PesapalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pesapal"

    def ready(self):
        import pesapal.signals
