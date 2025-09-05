from django.contrib import admin
from .models import csv_uryo, WatchStatus, ProcessedFile

@admin.register(csv_uryo)
class CsvUryoAdmin(admin.ModelAdmin):
    list_display = ['observation_datetime', 'station_name', 'region_name', 'observation_value', 'item_type']
    list_filter = ['region_name', 'item_type', 'observation_datetime']
    search_fields = ['station_name', 'unified_id']
    date_hierarchy = 'observation_datetime'
    ordering = ['-observation_datetime']

@admin.register(WatchStatus)
class WatchStatusAdmin(admin.ModelAdmin):
    list_display = ['is_watching', 'last_checked', 'processed_files_count', 'error_count']
    readonly_fields = ['last_checked']

@admin.register(ProcessedFile)
class ProcessedFileAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'processed_at', 'records_count', 'status', 'file_size']
    list_filter = ['status', 'processed_at']
    search_fields = ['file_name']
    readonly_fields = ['file_hash', 'processed_at']
    date_hierarchy = 'processed_at'
    ordering = ['-processed_at']
