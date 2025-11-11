from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    label = 'users'

    def ready(self):
        super().ready()
        import users.signals
