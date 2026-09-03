from django.db import migrations


def seed_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Role.objects.get_or_create(name="Admin")
    Role.objects.get_or_create(name="Operator")
    Role.objects.get_or_create(name="Viewer")


def reverse_seed(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Role.objects.filter(name__in=["Admin", "Operator", "Viewer"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),  # confirm this matches your actual filename
    ]
    operations = [
        migrations.RunPython(seed_roles, reverse_seed),
    ]