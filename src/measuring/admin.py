from django.contrib import admin

# Register your models here.
from .models import Parameter

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
	search_fields = ['name','title']
	list_filter = ['db_number','offset','field_type']
	list_display = ('name','title','db_number','offset','field_type','bit_number','user')

	readonly_fields = ('created','updated','user')

	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['name','title']}),
        ('PLC Information',{'fields': ['db_number','offset','field_type','bit_number']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]
