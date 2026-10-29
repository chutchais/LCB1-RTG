from django import forms

from .models import Failure, FailureCategory, Machine, Vendor


class ReportFailureForm(forms.ModelForm):
    machine = forms.ModelChoiceField(
        queryset=Machine.objects.select_related("machine_type").order_by("name"),
        label="หมายเลขเครื่อง",
        empty_label="เลือกเครื่องที่เสีย",
        error_messages={"required": "กรุณาเลือกเครื่อง", "invalid_choice": "กรุณาเลือกเครื่องจากรายการ"},
    )
    details = forms.CharField(
        label="เครื่องมีปัญหาอะไร?",
        max_length=200,
        error_messages={"required": "กรุณาบอกอาการเสียสั้น ๆ"},
        widget=forms.Textarea(attrs={
            "rows": 3, "placeholder": "เช่น สตาร์ทไม่ติด หรือ ยกตู้ไม่ได้",
            "aria-describedby": "details-help",
        }),
    )

    class Meta:
        model = Failure
        fields = ("machine", "details", "category")
        labels = {"category": "ประเภทงาน"}


class CompleteRepairForm(forms.Form):
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.order_by("name"),
        label="ผู้รับเหมาซ่อม / Vendor",
        required=False,
        empty_label="ไม่ระบุ / ซ่อมเอง",
    )
    repair_cost = forms.DecimalField(
        label="ค่าซ่อม (บาท)", required=False,
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal", "placeholder": "0.00"}),
    )
    service_cost = forms.DecimalField(
        label="ค่าบริการ (บาท)", required=False,
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal", "placeholder": "0.00"}),
    )
    rootcause = forms.CharField(
        label="สาเหตุที่ทำให้เครื่องเสีย",
        max_length=200,
        error_messages={"required": "กรุณาระบุสาเหตุก่อนปิดงาน"},
        widget=forms.Textarea(attrs={
            "rows": 3, "placeholder": "เช่น สายไฮดรอลิกเสื่อมสภาพจนรั่ว",
        }),
    )
    is_human_error = forms.BooleanField(
        label="เกี่ยวข้องกับความผิดพลาดของคน",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "aria-controls": "human-error-details",
            "aria-expanded": "false",
        }),
    )
    human_error_details = forms.CharField(
        label="เกิดความผิดพลาดอย่างไร?",
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3, "placeholder": "เช่น ใช้งานผิดขั้นตอน หรือไม่ได้ตรวจสอบก่อนใช้งาน",
        }),
    )
    failure_category = forms.ModelChoiceField(
        queryset=FailureCategory.objects.none(),
        label="ประเภทอาการเสีย",
        required=False,
        empty_label="ไม่แน่ใจ / ยังไม่ระบุ",
        error_messages={"invalid_choice": "กรุณาเลือกประเภทอาการเสียจากรายการของเครื่องนี้"},
    )
    repair_action = forms.CharField(
        label="ซ่อมอะไรไปบ้าง?",
        max_length=200,
        error_messages={"required": "กรุณาบอกสิ่งที่ซ่อมก่อนปิดงาน"},
        widget=forms.Textarea(attrs={
            "rows": 3, "placeholder": "เช่น เปลี่ยนสายไฮดรอลิก และทดสอบแล้ว",
        }),
    )

    def __init__(self, *args, failure, **kwargs):
        super().__init__(*args, **kwargs)
        if failure.machine_id and failure.machine.machine_type_id:
            self.fields["failure_category"].queryset = FailureCategory.objects.filter(
                machine_type_id=failure.machine.machine_type_id,
                is_active=True,
            ).order_by("order", "name")
        self.initial["failure_category"] = failure.failure_category_id
        self.initial.update({
            "vendor": failure.vendor_id,
            "repair_cost": failure.repair_cost,
            "service_cost": failure.service_cost,
            "rootcause": failure.rootcause,
            "is_human_error": failure.is_human_error,
            "human_error_details": failure.human_error_details,
        })
        for name in ("rootcause", "repair_action", "human_error_details"):
            self.fields[name].widget.attrs["rows"] = 2

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("is_human_error"):
            cleaned_data["human_error_details"] = ""
        return cleaned_data


class FailurePhotoForm(forms.Form):
    image = forms.ImageField(
        label="รูปภาพ",
        error_messages={
            "required": "กรุณาเลือกรูปภาพ",
            "invalid_image": "เปิดรูปนี้ไม่ได้ กรุณาใช้รูป JPG หรือ PNG",
        },
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
    )

    def clean_image(self):
        image = self.cleaned_data["image"]
        if image.size > 12 * 1024 * 1024:
            raise forms.ValidationError("รูปใหญ่เกินไป กรุณาใช้รูปขนาดไม่เกิน 12 MB")
        if image.image.format not in ("JPEG", "PNG", "WEBP"):
            raise forms.ValidationError("กรุณาใช้รูป JPG, PNG หรือ WebP")
        return image
