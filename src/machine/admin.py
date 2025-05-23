from django.contrib import admin

# Register your models here.
from .models import Equipment,Item,DataLogger

class ItemInline(admin.TabularInline):
	model = Item
	fields = ('seq','name','parameter','monitor','units','current_value')
	autocomplete_fields = ['parameter']
	extra = 1 # how many rows to show
	show_change_link = True

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
	search_fields = ['name','title','ip']
	list_filter = []
	list_display = ('name','title','ip','created','user')

	readonly_fields = ('created','updated','user')

	inlines = [
        ItemInline,
    ]
	save_as = True
	save_as_continue = True
	save_on_top =True
	list_select_related = True

	fieldsets = [
		('Basic Information',{'fields': ['name','title','ip']}),
		('System Information',{'fields':[('user','created'),'updated']})
	]

@admin.register(DataLogger)
class DataLoggerAdmin(admin.ModelAdmin):
	search_fields = ['item__equipment__name','item__parameter__name']
	list_filter = ['item__equipment__name','item__parameter__name']
	list_display = ('item','last_value','current_value','created')
	readonly_fields = ('created','updated')


	fieldsets = [
		('Basic Information',{'fields': ['item','last_value','current_value']}),
		('System Information',{'fields':['created','updated']})
	]