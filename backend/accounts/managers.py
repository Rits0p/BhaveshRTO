from django.contrib.auth.base_user import BaseUserManager


class AdminManager(BaseUserManager):
    """Manager for the single-admin `Admin` user model.

    `exists_already()` is the single source of truth the signup view (and
    the model's own `save()` guard) use to enforce that exactly one Admin
    row can ever exist for the lifetime of the system.
    """

    use_in_migrations = True

    def exists_already(self):
        return self.model.objects.exists()

    def _create(self, email, password, name, **extra_fields):
        if not email:
            raise ValueError('Admin must have an email address.')
        email = self.normalize_email(email)
        admin = self.model(email=email, name=name, **extra_fields)
        admin.set_password(password)
        admin.save(using=self._db)
        return admin

    def create_user(self, email, password, name='', **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create(email, password, name, **extra_fields)

    def create_superuser(self, email, password, name='Admin', **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        return self._create(email, password, name, **extra_fields)
