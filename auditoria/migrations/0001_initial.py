from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("action", models.CharField(db_index=True, max_length=50)),
                ("module", models.CharField(blank=True, default="", max_length=100)),
                ("entity_type", models.CharField(db_index=True, max_length=100)),
                ("entity_id", models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ("entity_repr", models.CharField(blank=True, default="", max_length=255)),
                ("before_state", models.JSONField(blank=True, null=True)),
                ("after_state", models.JSONField(blank=True, null=True)),
                ("request_id", models.CharField(db_index=True, max_length=36)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, default="")),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("success", models.BooleanField(default=True)),
                ("error_message", models.TextField(blank=True, null=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "auditoria_auditevent",
                "ordering": ["-timestamp", "-id"],
                "indexes": [
                    models.Index(fields=["entity_type", "entity_id"], name="audit_entity_idx"),
                    models.Index(fields=["actor"], name="audit_actor_idx"),
                    models.Index(fields=["action"], name="audit_action_idx"),
                    models.Index(fields=["request_id"], name="audit_request_idx"),
                ],
            },
        ),
    ]

