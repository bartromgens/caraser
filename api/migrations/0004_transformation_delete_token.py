import secrets

from django.db import migrations, models


def backfill_delete_tokens(apps, schema_editor):
    Transformation = apps.get_model("api", "Transformation")
    for obj in Transformation.objects.filter(delete_token=""):
        obj.delete_token = secrets.token_urlsafe()
        obj.save(update_fields=["delete_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_comparison_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="transformation",
            name="delete_token",
            field=models.CharField(default="", editable=False, max_length=64),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_delete_tokens, migrations.RunPython.noop),
    ]
