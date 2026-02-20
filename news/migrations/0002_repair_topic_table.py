from django.db import migrations

def create_topic_table(apps, schema_editor):
    Topic = apps.get_model("news", "Topic")
    table = Topic._meta.db_table
    existing = schema_editor.connection.introspection.table_names()
    if table not in existing:
        schema_editor.create_model(Topic)

class Migration(migrations.Migration):
    dependencies = [
        ("news", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_topic_table, migrations.RunPython.noop),
    ]