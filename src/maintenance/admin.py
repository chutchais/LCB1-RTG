from django.contrib import admin

# Register your models here.
from .models import Section,MachineType,Machine,Failure,Defect, \
				Preventive,Accident,AccidentImage,FailureImage,PreventiveImage, \
				Vendor
from django import forms
from django.db import models
from django.forms               import TextInput, Textarea
from base.utility import get_date_range,get_day_or_night_with_date
from django.utils.translation import gettext_lazy as _

# Register your models here.
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.admin import ImportExportActionModelAdmin
from import_export.fields import Field

class OperationDateListFilter(admin.SimpleListFilter):
	# Human-readable title which will be displayed in the
	# right admin sidebar just above the filter options.
	title = _('Operation Date range')

	# Parameter for the filter that will be used in the URL query.
	parameter_name = 'operation_date'

	def lookups(self, request, model_admin):
		"""
		Returns a list of tuples. The first element in each
		tuple is the coded value for the option that will
		appear in the URL query. The second element is the
		human-readable name for the option that will appear
		in the right sidebar.
		"""
		return (
		('yesterday', _('Yesterday')),
		('today', _('Today')),
		('thisweek', _('This week')),
		('lastweek', _('Last week')),
		('thismonth', _('This month')),
		('lastmonth', _('Last month')),
		('thisyear', _('This year')),
		('lastyear', _('Last year')),
		)

	def queryset(self, request, queryset):
		from datetime import datetime
		from django.utils import timezone
		tz = timezone.get_current_timezone()
		today = timezone.now().astimezone(tz).date()
		if not self.value():
			return queryset

		start_date,end_date = get_date_range(today,self.value())
		return queryset.filter(operation_date__range = [start_date, end_date]).order_by('start_date')

class MachineTypeInline(admin.TabularInline):
	model = MachineType
	fields = ['name','title']
	extra = 0
	show_change_link = True

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
	search_fields = ['name','title']
	list_filter = []
	list_display = ('name','title','machine_type_count','created','user')

	readonly_fields = ('created','updated','machine_type_count')

	inlines = [
        MachineTypeInline,
    ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['name','title']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]

	def save_model(self, request, obj, form, change):
		print(request.user)
		if not change:
			# Only set added_by during the first save.
			obj.user = request.user
		super().save_model(request, obj, form, change)


class MachineInline(admin.TabularInline):
	model = Machine
	fields = ['name','title','terminal']
	extra = 0
	show_change_link = True

@admin.register(MachineType)
class MachineTypeAdmin(admin.ModelAdmin):
	search_fields = ['name','title']
	list_filter = ['section']
	list_display = ('name','title','section','machine_count',
				 	'target','machine_on_working','machine_on_preventive','created','user')

	readonly_fields = ('created','updated','user','machine_count')

	inlines = [
        MachineInline,
    ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['name','title','section','target']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]
	def save_model(self, request, obj, form, change):
		# print(request.user)
		if not change:
			# Only set added_by during the first save.
			obj.user = request.user
		super().save_model(request, obj, form, change)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
	search_fields = ['name','title']
	list_filter = []
	list_display = ('name','title','created','user')

	readonly_fields = ('created','updated','user')

	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['name','title']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]
	def save_model(self, request, obj, form, change):
		# print(request.user)
		if not change:
			# Only set added_by during the first save.
			obj.user = request.user
		super().save_model(request, obj, form, change)

class FailureInline(admin.TabularInline):
	formfield_overrides = {
		models.CharField: {'widget': TextInput(attrs={'size':'50'})},
		models.TextField: {'widget': Textarea(attrs={'rows':3, 'cols':50})},
	}
	model = Failure
	fields = ['details','start_date','expect_date','end_date','status']
	extra = 0
	show_change_link = True
	def get_queryset(self, request):
		qs = super(FailureInline, self).get_queryset(request)
		return qs.filter(status='OPEN')

class PreventiveInline(admin.TabularInline):
	model = Preventive
	fields = ['details','period','period_unit','start_date','end_date','status']
	extra = 0
	show_change_link = True
	def get_queryset(self, request):
		qs = super(PreventiveInline, self).get_queryset(request)
		return qs.filter(status='WORKING')

class AccidentInline(admin.TabularInline):
	model = Accident
	fields = ['details','created','status']
	extra = 0
	show_change_link = True
	readonly_fields=['created']

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
	search_fields = ['name','title']
	list_filter = ['terminal','machine_type']
	list_display = ('name','title','terminal','on_repair','on_preventive','created','user')

	readonly_fields = ('created','updated','user','on_repair','on_preventive')

	inlines = [
        FailureInline,
		PreventiveInline,
		AccidentInline
    ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['name','title','terminal','machine_type']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]
	def save_model(self, request, obj, form, change):
		# print(request.user)
		if not change:
			# Only set added_by during the first save.
			obj.user = request.user
		super().save_model(request, obj, form, change)

class FailureImageInline(admin.TabularInline):
	model = FailureImage
	fields = ['details','image']
	extra = 0
	show_change_link = True

class DefectInline(admin.TabularInline):
	formfield_overrides = {
		models.CharField: {'widget': TextInput(attrs={'size':'50'})},
		models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':50})},
	}
	model = Defect
	fields = ['symptom_area','details','status','repair','repair_details','repair_done']
	extra = 0
	show_change_link = True
	# def get_queryset(self, request):
	# 	qs = super(FailureInline, self).get_queryset(request)
	# 	return qs.filter(status='OPEN')

class FailureResource(resources.ModelResource):
	# operation_date_field = Field(attribute='operation_date', column_name='operation_date')
	waitting_time = Field()
	repairing_time = Field()
	lead_time	= Field()
	

	class Meta:
		model = Failure
		Fields = ('machine','receiving_date','start_date','end_date','repairing_time',
				'lead_time','waitting_time','detail','category',
		   		'rootcause','repair_action','operation_date','operation_shift','status',)
		exclude  =('id','created','updated','created_year','created_month',
			 'created_day','created_hour','created_week','expect_date',)
		
		widgets = {
            'operation_date': {'format': '%b %d, %Y'},
        }
	
	def dehydrate_repairing_time(self, failure):
		return failure.repairing_time/60
	
	def dehydrate_lead_time(self, failure):
		return failure.lead_time/60

	def dehydrate_waitting_time(self, failure):
		return failure.waitting_time/60
	# def dehydrate_operation_date(self, failure):
	# 	return failure


@admin.register(Failure)
class FailureAdmin(ImportExportModelAdmin,ImportExportActionModelAdmin,admin.ModelAdmin):
	formfield_overrides = {
	models.CharField: {'widget': TextInput(attrs={'size':'50'})},
	models.TextField: {'widget': Textarea(attrs={'rows':3, 'cols':50})},
	}
	search_fields = ['machine__name','details','rootcause','repair_action']
	list_filter = [OperationDateListFilter,'operation_shift','status','category','machine__machine_type','vendor']
	list_display = ('machine','details','receiving_date','start_date','end_date','status','category','image_count',
				 'defect_count','user')

	readonly_fields = ('created','updated','user','defect_count',
					'operation_date','operation_shift','repairing_time','lead_time','waitting_time')
	autocomplete_fields  = ['machine','vendor']
	inlines = [
		FailureImageInline,
        DefectInline,
    ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	resource_class      = FailureResource

	fieldsets = [
		('Basic Information',{'fields': ['machine','details','category']}),
		('Plan Information',{'fields': ['receiving_date','start_date','status','end_date',
								  'operation_date','operation_shift',
								  'waitting_time','repairing_time','lead_time']}),
		('Failure Analysis',{'fields': ['rootcause','repair_action']}),
		('Vendor and Cost Information',{'fields': ['vendor','repair_cost','service_cost']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]
	def save_model(self, request, obj, form, change):
		# print(request.user)
		if not change:
			# Only set added_by during the first save.
			obj.user = request.user
		# if obj.end_date:
		if obj.receiving_date :
			# Timezone awareness
			from django.utils import timezone
			tz = timezone.get_current_timezone()
			operation_date,operation_shift = get_day_or_night_with_date(obj.receiving_date.astimezone(tz))
			# print(operation_date,operation_shift,obj.end_date)
			obj.operation_date	=	operation_date
			obj.operation_shift	=	operation_shift
		super().save_model(request, obj, form, change)

@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
	formfield_overrides = {
		models.CharField: {'widget': TextInput(attrs={'size':'50'})},
		models.TextField: {'widget': Textarea(attrs={'rows':3, 'cols':50})},
	}
	search_fields = ['failure__details','details']
	list_filter = ['status','repair_done','symptom_area']
	list_display = ('failure','details','status','created','user')

	readonly_fields = ('created','updated','user')
	autocomplete_fields  = ['failure']
	# inlines = [
    #     ItemInline,
    # ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['failure','details','status']}),
		('Defect Information',{'fields': ['symptom_area']}),
		('Repair Information',{'fields': ['repair','repair_details','repair_done']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]
	def formfield_for_foreignkey(self, db_field, request, **kwargs):  
		if db_field.name == "failure":  # ตัวอย่างการกรอง foreign key game  
			kwargs["queryset"] = Failure.objects.filter(status='OPEN')  # ปรับให้แสดงเฉพาะเกมที่ active  
		return super().formfield_for_foreignkey(db_field, request, **kwargs)
	def save_model(self, request, obj, form, change):
		# print(request.user)
		if not change:
			# Only set added_by during the first save.
			obj.user = request.user
		super().save_model(request, obj, form, change)

# Added on Dec 19,2024 -- To support Image
class PreventiveImageInline(admin.TabularInline):
	model = PreventiveImage
	fields = ['details','image']
	extra = 0
	show_change_link = True

@admin.register(Preventive)
class PreventiveAdmin(admin.ModelAdmin):
	formfield_overrides = {
		models.CharField: {'widget': TextInput(attrs={'size':'50'})},
		models.TextField: {'widget': Textarea(attrs={'rows':3, 'cols':50})},
	}
	search_fields = ['machine__name','details']
	list_filter = ['status','machine__machine_type','period']
	list_display = ('machine','details','period','period_unit','start_date','end_date','status','created','user')

	readonly_fields = ('created','updated','user')
	autocomplete_fields  = ['machine']
	inlines = [
        PreventiveImageInline,
    ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['machine','details','period','period_unit']}),
		('Plan Information',{'fields': ['start_date','end_date','status']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]
	def save_model(self, request, obj, form, change):
		# print(request.user)
		if not change:
			# Only set added_by during the first save.
			obj.user = request.user
		super().save_model(request, obj, form, change)


class AccidentImageInline(admin.TabularInline):
	model = AccidentImage
	fields = ['details','image']
	extra = 0
	show_change_link = True
	# def get_queryset(self, request):
	# 	qs = super(PreventiveInline, self).get_queryset(request)
	# 	return qs.filter(status='WORKING')
	
@admin.register(Accident)
class AccidentAdmin(admin.ModelAdmin):
	formfield_overrides = {
	models.CharField: {'widget': TextInput(attrs={'size':'50'})},
	models.TextField: {'widget': Textarea(attrs={'rows':3, 'cols':50})},
	}
	search_fields = ['machine__name','details']
	list_filter = ['created','machine__machine_type','status']
	list_display = ('machine','details','image_count','status','created','user')

	readonly_fields = ('created','updated','user','image_count')
	autocomplete_fields  = ['machine']
	inlines = [
        AccidentImageInline,
    ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['machine','details']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]
	def save_model(self, request, obj, form, change):
		# print(request.user)
		if not change:
			# Only set added_by during the first save.
			obj.user = request.user
		super().save_model(request, obj, form, change)