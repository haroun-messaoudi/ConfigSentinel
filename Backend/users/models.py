from django.contrib.auth.models import AbstractUser, Permission, UserManager
from django.db import models


class Role(models.Model):
    """A named set of permissions — Admin, Operator, Viewer, etc."""
    name = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
    )

    def __str__(self):
        return self.name


class CustomUserManager(UserManager):
    def create_superuser(
        self,
        username,
        email=None,
        password=None,
        **extra_fields
    ):
        role = Role.objects.get(name="Admin")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields["role"] = role

        return super().create_superuser(
            username,
            email,
            password,
            **extra_fields,
        )


class User(AbstractUser):
    role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    objects = CustomUserManager()

    def has_perm(self, perm, obj=None):
        if self.is_superuser:
            return True

        if self.role is None:
            return False

        _, codename = perm.split(".", 1)

        return self.role.permissions.filter(
            codename=codename
        ).exists()