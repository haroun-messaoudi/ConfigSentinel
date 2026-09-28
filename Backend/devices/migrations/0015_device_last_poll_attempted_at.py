from django.db import migrations, models


def backfill_poll_timestamps(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    Snapshot = apps.get_model("devices", "Snapshot")
    database = schema_editor.connection.alias

    for device in Device.objects.using(database).all().iterator():
        previous_poll_time = device.last_polled_at
        device.last_poll_attempted_at = previous_poll_time

        if device.last_poll_status == "ERROR":
            device.last_polled_at = (
                Snapshot.objects.using(database)
                .filter(device_id=device.pk)
                .order_by("-taken_at")
                .values_list("taken_at", flat=True)
                .first()
            )

        device.save(
            using=database,
            update_fields=["last_poll_attempted_at", "last_polled_at"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0014_configchange_change_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="last_poll_attempted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_poll_timestamps, migrations.RunPython.noop),
    ]