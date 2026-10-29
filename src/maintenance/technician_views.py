import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps
from redis import Redis
from redis.exceptions import RedisError

from base.utility import get_day_or_night_with_date
from .forms import CompleteRepairForm, FailurePhotoForm, ReportFailureForm, StartRepairForm
from .models import Failure, FailureImage
from .mosquitto import db as mqtt_db


logger = logging.getLogger(__name__)
LOGIN_URL = "maintenance:technician-login"


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _capture_readings(failure):
    # Capture once at reporting; later saves must not replace the historical readings.
    try:
        connection = {
            **mqtt_db.connection_pool.connection_kwargs,
            "socket_connect_timeout": 1,
            "socket_timeout": 1,
        }
        with Redis(**connection) as readings:
            hour, move, malfunction = readings.mget([
                f"{failure.machine_id}:hour",
                f"{failure.machine_id}:move",
                f"{failure.machine_id}:malfunction",
            ])
        if hour is not None:
            value = Decimal(hour)
            if value.is_finite() and 0 <= value <= Decimal("99999999.99"):
                failure.engine_hour = value
        if move is not None:
            value = int(move)
            if 0 <= value <= 2147483647:
                failure.engine_move = value
        if malfunction in ("0", "1"):
            failure.engine_malfunction = malfunction
    except (RedisError, ValueError, TypeError, InvalidOperation):
        logger.warning("Equipment readings unavailable for %s", failure.machine_id)


@login_required(login_url=LOGIN_URL)
@permission_required("maintenance.view_failure", raise_exception=True)
def job_board(request):
    status = "CLOSED" if request.GET.get("status") == "closed" else "OPEN"
    query = request.GET.get("q", "").strip()
    jobs = Failure.objects.filter(status=status).select_related("machine__machine_type")
    if query:
        jobs = jobs.filter(Q(machine__name__icontains=query) | Q(details__icontains=query))
    elif status == "CLOSED":
        now = timezone.now()
        jobs = jobs.filter(end_date__gte=now - timedelta(days=1), end_date__lte=now)
    ordering = "-end_date" if status == "CLOSED" else "-created"
    page = Paginator(jobs.order_by(ordering, "-pk"), 20).get_page(request.GET.get("page"))
    groups = {}
    for job in page:
        machine_type = job.machine.machine_type_id if job.machine_id else None
        groups.setdefault(machine_type or "ไม่ระบุประเภท", []).append(job)
    return render(request, "maintenance/technician/board.html", {
        "page_obj": page, "query": query, "closed": status == "CLOSED",
        "job_columns": [
            {"name": name, "jobs": groups[name]} for name in sorted(groups)
        ],
    })


@login_required(login_url=LOGIN_URL)
@permission_required(("maintenance.add_failure", "maintenance.view_failure"), raise_exception=True)
def report_failure(request):
    form = ReportFailureForm(request.POST if request.method == "POST" else None)
    if request.method == "POST":
        if form.is_valid():
            failure = form.save(commit=False)
            failure.user = request.user
            failure.receiving_date = timezone.now()
            failure.operation_date, failure.operation_shift = get_day_or_night_with_date(
                timezone.localtime(failure.receiving_date)
            )
            # Unknown hours remain distinct from an actual zero-hour reading.
            failure.engine_hour = None
            _capture_readings(failure)
            failure.save()
            url = reverse("maintenance:technician-job", args=[failure.pk])
            if _is_ajax(request):
                return JsonResponse({
                    "url": url,
                    "upload_url": reverse("maintenance:technician-photo", args=[failure.pk]),
                    "job_id": failure.pk,
                }, status=201)
            messages.success(request, "บันทึกแจ้งซ่อมแล้ว")
            return redirect(url)
        if _is_ajax(request):
            return JsonResponse({"errors": form.errors}, status=400)
    open_jobs = [{
        "machine": job.machine_id,
        "url": reverse("maintenance:technician-job", args=[job.pk]),
    } for job in Failure.objects.filter(status="OPEN").only("machine_id").order_by("-created")]
    return render(request, "maintenance/technician/report.html", {
        "form": form, "open_jobs": open_jobs,
    })


def _job_context(failure, complete_form=None, photo_form=None, start_form=None):
    if complete_form is None:
        complete_form = CompleteRepairForm(failure=failure)
    return {
        "job": failure,
        "start_form": start_form if start_form is not None else StartRepairForm(
            initial={"expect_date": failure.expect_date} if failure.expect_date else None,
        ),
        "complete_form": complete_form,
        "failure_category_tree": list(
            complete_form.fields["failure_category"].queryset.values("id", "name", "parent_id")
        ),
        "photo_form": photo_form if photo_form is not None else FailurePhotoForm(),
    }


@login_required(login_url=LOGIN_URL)
@permission_required("maintenance.view_failure", raise_exception=True)
def job_detail(request, pk):
    failure = get_object_or_404(Failure.objects.select_related("machine"), pk=pk)
    return render(request, "maintenance/technician/job.html", _job_context(failure))


@login_required(login_url=LOGIN_URL)
@permission_required(("maintenance.change_failure", "maintenance.view_failure"), raise_exception=True)
@require_POST
def job_action(request, pk):
    with transaction.atomic():
        failure = get_object_or_404(Failure.objects.select_for_update(), pk=pk)
        now = timezone.now()
        if failure.status == "CLOSED":
            messages.info(request, "งานนี้ซ่อมเสร็จแล้ว")
        elif request.POST.get("action") == "start":
            if failure.receiving_date and failure.receiving_date > now:
                messages.error(request, "เวลาแจ้งซ่อมอยู่ในอนาคต กรุณาให้ผู้ดูแลตรวจสอบ")
            elif not failure.start_date:
                form = StartRepairForm(request.POST)
                if not form.is_valid():
                    return render(
                        request, "maintenance/technician/job.html",
                        _job_context(failure, start_form=form), status=400,
                    )
                failure.start_date = now
                failure.expect_date = form.cleaned_data["expect_date"]
                failure.save(update_fields=["start_date", "expect_date", "updated"])
                messages.success(request, "บันทึกเริ่มซ่อมแล้ว")
        elif request.POST.get("action") == "update_expected":
            form = StartRepairForm(request.POST)
            if not form.is_valid():
                return render(
                    request, "maintenance/technician/job.html",
                    _job_context(failure, start_form=form), status=400,
                )
            failure.expect_date = form.cleaned_data["expect_date"]
            failure.save(update_fields=["expect_date", "updated"])
            messages.success(request, "เปลี่ยนเวลาคาดว่าจะซ่อมเสร็จแล้ว")
        elif request.POST.get("action") == "complete":
            form = CompleteRepairForm(request.POST, failure=failure)
            if not failure.start_date:
                messages.error(request, "กรุณากดเริ่มซ่อมก่อน")
            elif failure.start_date > now or (
                failure.receiving_date and failure.start_date < failure.receiving_date
            ):
                messages.error(request, "เวลาของงานไม่ถูกต้อง กรุณาให้ผู้ดูแลตรวจสอบ")
            elif form.is_valid():
                failure.repair_action = form.cleaned_data["repair_action"]
                failure.rootcause = form.cleaned_data["rootcause"]
                failure.is_human_error = form.cleaned_data["is_human_error"]
                failure.human_error_details = form.cleaned_data["human_error_details"]
                failure.vendor = form.cleaned_data["vendor"]
                failure.repair_cost = form.cleaned_data["repair_cost"]
                failure.service_cost = form.cleaned_data["service_cost"]
                if form.cleaned_data["failure_category"] is not None:
                    failure.failure_category = form.cleaned_data["failure_category"]
                failure.end_date = now
                failure.status = "CLOSED"
                failure.save(update_fields=[
                    "repair_action", "rootcause", "is_human_error", "human_error_details",
                    "vendor", "repair_cost", "service_cost",
                    "failure_category", "end_date", "status", "updated",
                ])
                messages.success(request, "บันทึกซ่อมเสร็จแล้ว ขอบคุณครับ")
            else:
                return render(
                    request, "maintenance/technician/job.html",
                    _job_context(failure, complete_form=form), status=400,
                )
        else:
            return JsonResponse({"error": "ไม่พบคำสั่งนี้"}, status=400)
    return redirect("maintenance:technician-job", pk=pk)


@login_required(login_url=LOGIN_URL)
@permission_required(
    ("maintenance.add_failureimage", "maintenance.change_failure", "maintenance.view_failure"),
    raise_exception=True,
)
@require_POST
def upload_photo(request, pk):
    failure = get_object_or_404(Failure.objects.select_related("machine"), pk=pk)
    form = FailurePhotoForm(request.POST, request.FILES)
    valid = form.is_valid()
    if not failure.machine_id:
        form.add_error("image", "งานนี้ยังไม่มีหมายเลขเครื่อง กรุณาให้ผู้ดูแลระบุเครื่องก่อนเพิ่มรูป")
        valid = False
    if valid:
        stored = None
        try:
            source = form.cleaned_data["image"]
            source.seek(0)
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((1920, 1920))
                image = image.convert("RGB")
                output = BytesIO()
                image.save(output, format="JPEG", quality=82)
            photo = FailureImage(failure=failure, user=request.user)
            photo.image.save(f"{uuid4().hex}.jpg", ContentFile(output.getvalue()), save=False)
            stored = photo.image
            with transaction.atomic():
                photo.save()
        except (OSError, ValueError, DatabaseError):
            if stored:
                try:
                    stored.delete(save=False)
                except OSError:
                    logger.exception("Could not remove failed photo upload")
            logger.exception("Could not save photo for repair job %s", failure.pk)
            form.add_error("image", "อัปโหลดไม่สำเร็จ งานซ่อมยังอยู่ กรุณาลองส่งรูปอีกครั้ง")
        else:
            if _is_ajax(request):
                return JsonResponse({"id": photo.pk, "url": photo.image.url}, status=201)
            messages.success(request, "บันทึกรูปแล้ว")
            return redirect("maintenance:technician-job", pk=pk)
    if _is_ajax(request):
        return JsonResponse({"errors": form.errors}, status=400)
    return render(
        request, "maintenance/technician/job.html",
        _job_context(failure, photo_form=form), status=400,
    )
