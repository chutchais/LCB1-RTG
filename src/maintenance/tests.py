from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from redis.exceptions import ConnectionError

from .models import Failure, FailureCategory, FailureImage, Machine, MachineType


class TechnicianWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.technician = get_user_model().objects.create_user("technician", password="test-pass")
        cls.technician.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="maintenance",
            codename__in=("view_failure", "add_failure", "change_failure", "add_failureimage"),
        ))
        machine_type = MachineType.objects.create(name="RTG")
        cls.machine = Machine.objects.create(name="RTG01", machine_type=machine_type)
        cls.other_machine = Machine.objects.create(name="RTG02", machine_type=machine_type)

    def setUp(self):
        self.client.force_login(self.technician)
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        override = self.settings(MEDIA_ROOT=self.media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.readings = patch("maintenance.technician_views.Redis")
        self.redis = self.readings.start()
        self.addCleanup(self.readings.stop)
        self.redis.return_value.__enter__.return_value.mget.return_value = [None, None, None]

    def url(self, name, job=None):
        return reverse(f"maintenance:technician-{name}", args=[job.pk] if job else [])

    def job(self, **kwargs):
        values = {
            "machine": self.machine, "details": "Engine will not start",
            "receiving_date": timezone.now() - timedelta(hours=1),
            "user": self.technician,
        }
        values.update(kwargs)
        return Failure.objects.create(**values)

    def photo(self, size=(60, 40)):
        output = BytesIO()
        Image.new("RGB", size, "blue").save(output, "PNG")
        return SimpleUploadedFile("camera.png", output.getvalue(), content_type="image/png")

    def test_login_is_available_to_non_staff_and_requires_permissions(self):
        self.client.logout()
        response = self.client.get(self.url("board"))
        self.assertRedirects(
            response, f'{self.url("login")}?next={self.url("board")}',
            fetch_redirect_response=False,
        )
        response = self.client.post(self.url("login"), {
            "username": "technician", "password": "test-pass",
        })
        self.assertRedirects(response, self.url("board"))
        unprivileged = get_user_model().objects.create_user("no-permissions")
        self.client.force_login(unprivileged)
        self.assertEqual(self.client.get(self.url("board")).status_code, 403)
        self.assertEqual(self.client.post(self.url("report"), {
            "machine": self.machine.pk, "details": "test",
        }).status_code, 403)
        job = self.job()
        self.assertEqual(self.client.get(self.url("job", job)).status_code, 403)
        self.assertEqual(self.client.post(self.url("action", job), {"action": "start"}).status_code, 403)
        self.assertEqual(self.client.post(self.url("photo", job), {"image": self.photo()}).status_code, 403)

    def test_reporting_preserves_shift_and_readings_without_trusting_hidden_fields(self):
        now = datetime(2026, 10, 28, 0, 30, tzinfo=datetime_timezone.utc)  # 07:30 Bangkok
        self.redis.return_value.__enter__.return_value.mget.return_value = ["1234.50", "120", "1"]
        with patch("maintenance.technician_views.timezone.now", return_value=now):
            response = self.client.post(self.url("report"), {
                "machine": self.machine.pk, "details": "ยกตู้ไม่ได้",
                "status": "CLOSED", "user": "999", "category": "CM",
            }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 201)
        job = Failure.objects.get()
        self.assertEqual(job.status, "OPEN")
        self.assertEqual(job.category, "CM")
        self.assertEqual(job.user, self.technician)
        self.assertEqual(job.receiving_date, now)
        self.assertEqual(str(job.operation_date), "2026-10-27")
        self.assertEqual(job.operation_shift, "Night")
        self.assertIsNone(job.start_date)
        self.assertEqual(job.engine_hour, Decimal("1234.50"))
        self.assertEqual(job.engine_move, 120)
        self.assertEqual(job.engine_malfunction, "1")
        self.assertEqual(response.json()["url"], self.url("job", job))
        self.assertEqual(self.redis.call_args.kwargs["socket_timeout"], 1)

    def test_reporting_works_when_readings_are_unavailable(self):
        self.redis.return_value.__enter__.return_value.mget.side_effect = ConnectionError("offline")
        response = self.client.post(self.url("report"), {
            "machine": self.machine.pk, "details": "สตาร์ทไม่ติด",
        })
        job = Failure.objects.get()
        self.assertRedirects(response, self.url("job", job))
        self.assertIsNone(job.engine_hour)

    def test_invalid_report_preserves_values_and_does_not_create_job(self):
        response = self.client.post(self.url("report"), {
            "machine": "", "details": "อาการที่พิมพ์ไว้",
        })
        self.assertContains(response, "อาการที่พิมพ์ไว้")
        self.assertTrue(response.context["form"].errors)
        response = self.client.post(self.url("report"), {
            "machine": "not-a-machine", "details": "x" * 201,
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertIn("machine", response.json()["errors"])
        self.assertIn("details", response.json()["errors"])
        self.assertFalse(Failure.objects.exists())

    def test_board_search_closed_filter_and_duplicate_warning_data(self):
        open_job = self.job()
        closed_job = self.job(machine=self.other_machine, status="CLOSED")
        response = self.client.get(self.url("board"))
        self.assertContains(response, self.url("job", open_job))
        self.assertNotContains(response, self.url("job", closed_job))
        response = self.client.get(self.url("board"), {"status": "closed", "q": "RTG02"})
        self.assertContains(response, self.url("job", closed_job))
        response = self.client.get(self.url("report"))
        self.assertEqual(response.context["open_jobs"], [{
            "machine": self.machine.pk, "url": self.url("job", open_job),
        }])

    def test_board_paginates_beyond_twenty_jobs(self):
        for number in range(21):
            self.job(details=f"Problem {number}")
        response = self.client.get(self.url("board"), {"page": 2})
        self.assertEqual(len(response.context["page_obj"]), 1)

    def test_start_then_complete_is_idempotent_and_preserves_reporting_metadata(self):
        job = self.job(engine_hour=Decimal("35.50"), operation_shift="Night")
        response = self.client.post(self.url("action", job), {"action": "start"})
        self.assertRedirects(response, self.url("job", job))
        job.refresh_from_db()
        started = job.start_date
        self.assertIsNotNone(started)
        self.client.post(self.url("action", job), {"action": "start"})
        job.refresh_from_db()
        self.assertEqual(job.start_date, started)
        self.client.post(self.url("action", job), {"action": "complete", "repair_action": "เปลี่ยนสายไฟ"})
        job.refresh_from_db()
        self.assertEqual(job.status, "CLOSED")
        self.assertEqual(job.repair_action, "เปลี่ยนสายไฟ")
        self.assertGreaterEqual(job.end_date, started)
        self.assertEqual(job.engine_hour, Decimal("35.50"))
        self.assertEqual(job.operation_shift, "Night")
        ended = job.end_date
        self.client.post(self.url("action", job), {"action": "complete", "repair_action": "overwrite"})
        job.refresh_from_db()
        self.assertEqual(job.end_date, ended)
        self.assertEqual(job.repair_action, "เปลี่ยนสายไฟ")

    def test_cannot_complete_before_start_or_with_invalid_times(self):
        job = self.job()
        self.client.post(self.url("action", job), {"action": "complete", "repair_action": "test"})
        job.refresh_from_db()
        self.assertEqual(job.status, "OPEN")
        job.start_date = timezone.now() + timedelta(hours=1)
        job.save()
        self.client.post(self.url("action", job), {"action": "complete", "repair_action": "test"})
        job.refresh_from_db()
        self.assertEqual(job.status, "OPEN")
        job.start_date = job.receiving_date - timedelta(minutes=1)
        job.save()
        self.client.post(self.url("action", job), {"action": "complete", "repair_action": "test"})
        job.refresh_from_db()
        self.assertEqual(job.status, "OPEN")

    def test_completion_category_is_filtered_and_saved(self):
        root = FailureCategory.objects.create(
            name="Engine", machine_type=self.machine.machine_type,
        )
        category = FailureCategory.objects.create(
            name="Injector", machine_type=self.machine.machine_type, parent=root,
        )
        inactive = FailureCategory.objects.create(
            name="Inactive", machine_type=self.machine.machine_type, is_active=False,
        )
        other = FailureCategory.objects.create(
            name="Other machine", machine_type=MachineType.objects.create(name="HUSTLER"),
        )
        job = self.job(start_date=timezone.now(), failure_category=category)
        response = self.client.get(self.url("job", job))
        form = response.context["complete_form"]
        self.assertSetEqual(set(form.fields["failure_category"].queryset), {root, category})
        self.assertEqual(form.initial["failure_category"], category.pk)
        self.assertContains(response, 'name="failure_category"')
        self.assertContains(response, "Engine &gt; Injector")
        for invalid in (inactive, other):
            with self.subTest(category=invalid.name):
                response = self.client.post(self.url("action", job), {
                    "action": "complete", "repair_action": "Replaced injector",
                    "failure_category": invalid.pk,
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn("failure_category", response.context["complete_form"].errors)
                job.refresh_from_db()
                self.assertEqual(job.status, "OPEN")
        response = self.client.post(self.url("action", job), {
            "action": "complete", "repair_action": "Replaced injector",
            "failure_category": root.pk,
        })
        self.assertRedirects(response, self.url("job", job))
        job.refresh_from_db()
        self.assertEqual(job.failure_category, root)
        self.assertEqual(job.status, "CLOSED")

    def test_optional_completion_category_preserves_existing_classification(self):
        category = FailureCategory.objects.create(
            name="Engine", machine_type=self.machine.machine_type,
        )
        job = self.job(start_date=timezone.now(), failure_category=category)
        self.client.post(self.url("action", job), {
            "action": "complete", "repair_action": "Repaired", "failure_category": "",
        })
        job.refresh_from_db()
        self.assertEqual(job.status, "CLOSED")
        self.assertEqual(job.failure_category, category)

    def test_future_reported_time_cannot_start(self):
        job = self.job(receiving_date=timezone.now() + timedelta(hours=1))
        self.client.post(self.url("action", job), {"action": "start"})
        job.refresh_from_db()
        self.assertIsNone(job.start_date)

    def test_completion_requires_description_and_preserves_it_on_error(self):
        job = self.job(start_date=timezone.now())
        response = self.client.post(self.url("action", job), {
            "action": "complete", "repair_action": "x" * 201,
        })
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "x" * 201, status_code=400)
        self.assertTrue(response.context["complete_form"].errors)
        job.refresh_from_db()
        self.assertEqual(job.status, "OPEN")

    def test_photo_upload_resizes_and_saves_to_existing_job(self):
        job = self.job(status="CLOSED")
        response = self.client.post(self.url("photo", job), {
            "image": self.photo(size=(3000, 1500)),
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 201)
        photo = FailureImage.objects.get()
        self.assertEqual(photo.user, self.technician)
        self.assertEqual(photo.failure, job)
        with Image.open(photo.image.path) as stored:
            self.assertEqual(stored.format, "JPEG")
            self.assertEqual(stored.size, (1920, 960))
        job.refresh_from_db()
        self.assertEqual(job.status, "CLOSED")

    def test_invalid_photo_does_not_lose_job_and_valid_retry_works(self):
        job = self.job()
        response = self.client.post(self.url("photo", job), {
            "image": SimpleUploadedFile("fake.jpg", b"not an image", content_type="image/jpeg"),
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.json()["errors"])
        self.assertTrue(Failure.objects.filter(pk=job.pk).exists())
        self.assertFalse(FailureImage.objects.exists())
        response = self.client.post(self.url("photo", job), {"image": self.photo()})
        self.assertRedirects(response, self.url("job", job))
        self.assertEqual(job.images.count(), 1)

    def test_storage_failure_leaves_job_available_for_retry(self):
        job = self.job()
        with patch("django.core.files.storage.FileSystemStorage._save", side_effect=OSError("disk full")):
            response = self.client.post(self.url("photo", job), {"image": self.photo()},
                                        HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(FailureImage.objects.exists())
        self.assertTrue(Failure.objects.filter(pk=job.pk).exists())

    def test_database_failure_removes_uploaded_file_without_losing_job(self):
        job = self.job()
        with patch("maintenance.technician_views.FailureImage.save", side_effect=DatabaseError("offline")):
            response = self.client.post(self.url("photo", job), {"image": self.photo()},
                                        HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(Path(self.media.name).rglob("*.jpg")), [])
        self.assertTrue(Failure.objects.filter(pk=job.pk).exists())

    def test_legacy_job_without_machine_has_clear_photo_error(self):
        job = self.job(machine=None)
        response = self.client.post(self.url("photo", job), {"image": self.photo()},
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.json()["errors"])
        self.assertFalse(FailureImage.objects.exists())

    def test_oversize_photo_is_rejected(self):
        job = self.job()
        photo = self.photo()
        photo = SimpleUploadedFile("large.png", photo.read() + b"0" * (12 * 1024 * 1024),
                                   content_type="image/png")
        response = self.client.post(self.url("photo", job), {"image": photo},
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(FailureImage.objects.exists())

    def test_mutations_require_post_and_csrf(self):
        job = self.job()
        self.assertEqual(self.client.get(self.url("logout")).status_code, 405)
        self.assertEqual(self.client.get(self.url("action", job)).status_code, 405)
        self.assertEqual(self.client.get(self.url("photo", job)).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.technician)
        for name in ("action", "photo"):
            self.assertEqual(protected.post(self.url(name, job)).status_code, 403)
        self.assertEqual(protected.post(self.url("report")).status_code, 403)

    def test_view_only_user_cannot_change_job_or_upload(self):
        viewer = get_user_model().objects.create_user("viewer")
        viewer.user_permissions.add(Permission.objects.get(
            content_type__app_label="maintenance", codename="view_failure",
        ))
        self.client.force_login(viewer)
        job = self.job()
        response = self.client.get(self.url("job", job))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="photo-form"')
        self.assertNotContains(response, 'name="action"')
        self.assertEqual(self.client.post(self.url("action", job), {"action": "start"}).status_code, 403)
        self.assertEqual(self.client.post(self.url("photo", job), {"image": self.photo()}).status_code, 403)
