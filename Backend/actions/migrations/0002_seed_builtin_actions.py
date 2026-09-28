from django.db import migrations


def create_builtin_actions(apps, schema_editor):
    ActionDefinition = apps.get_model("actions", "ActionDefinition")
    ActionParameter = apps.get_model("actions", "ActionParameter")
    ActionTemplate = apps.get_model("actions", "ActionTemplate")

    # 1. Create Action Definition: Add ACL Entry
    action_def, _ = ActionDefinition.objects.get_or_create(
        name="Add ACL Entry",
        defaults={"description": "Appends an extended access list rule to a Cisco XE device."}
    )

    # 2. Define Parameters with type enforcement and regex rules
    parameters_data = [
        {"name": "acl_name", "label": "ACL Name or Number", "data_type": "STRING", "is_required": True, "validation_regex": r"^[A-Za-z0-9_-]+$"},
        {"name": "action", "label": "Action (permit/deny)", "data_type": "STRING", "is_required": True, "validation_regex": r"^(permit|deny)$"},
        {"name": "protocol", "label": "Protocol", "data_type": "STRING", "is_required": True, "default_value": "ip"},
        {"name": "source_ip", "label": "Source IP or 'any'", "data_type": "STRING", "is_required": True},
        {"name": "destination_ip", "label": "Destination IP or 'any'", "data_type": "STRING", "is_required": True},
    ]

    for p_data in parameters_data:
        ActionParameter.objects.get_or_create(
            action_definition=action_def,
            name=p_data["name"],
            defaults=p_data
        )

    # 3. Create Template for Cisco XE devices (Explicitly blocks switches/other device types lacking templates)
    cisco_template_text = (
        "ip access-list extended {{ acl_name }}\n"
        " {{ action }} {{ protocol }} {{ source_ip }} {{ destination_ip }}"
    )
    
    ActionTemplate.objects.get_or_create(
        action_definition=action_def,
        device_type="cisco_xe",
        defaults={"template_text": cisco_template_text}
    )


def reverse_builtin_actions(apps, schema_editor):
    ActionDefinition = apps.get_model("actions", "ActionDefinition")
    ActionDefinition.objects.filter(name="Add ACL Entry").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("actions", "0001_initial"),  # Update with your app's actual prior migration name
    ]

    operations = [
        migrations.RunPython(create_builtin_actions, reverse_builtin_actions),
    ]