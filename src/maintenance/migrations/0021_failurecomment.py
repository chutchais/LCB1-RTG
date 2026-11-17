import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import maintenance.models


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0020_add_cmrp_field"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FailureComment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True, null=True)),
                ("status", models.BooleanField(default=True)),
                ("created_year", models.PositiveSmallIntegerField(default=2022)),
                ("created_month", models.PositiveSmallIntegerField(default=1)),
                ("created_day", models.PositiveSmallIntegerField(default=1)),
                ("created_hour", models.PositiveSmallIntegerField(default=0)),
                ("created_week", models.PositiveSmallIntegerField(default=1)),
                ("text", models.TextField(blank=True, max_length=2000)),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        upload_to=maintenance.models.failure_comment_upload_path,
                    ),
                ),
                (
                    "failure",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="maintenance.failure",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="failure_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ma-failure-comment",
                "ordering": ("created", "pk"),
                "abstract": False,
            },
        ),
    ]
