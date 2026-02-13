from django.contrib import admin
from .models import (
    UserSettings, CallRecord, TrackingRecord, DailyTask, Note,
    HelpTopic, HelpTab
)

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'schedule_type', 'first_work_date', 'sound_enabled', 'volume', 'dark_theme')
    list_filter = ('schedule_type', 'sound_enabled', 'dark_theme')
    search_fields = ('user__username',)

@admin.register(CallRecord)
class CallRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone', 'next_attempt', 'call_type')
    list_filter = ('user', 'call_type', 'attempt_number')
    search_fields = ('phone', 'comment')

@admin.register(TrackingRecord)
class TrackingRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'claim', 'crm', 'connection_datetime', 'status')
    list_filter = ('user', 'status')
    search_fields = ('claim', 'crm')

@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'task', 'completed')
    list_filter = ('user', 'date', 'completed')
    search_fields = ('task',)

admin.site.register(Note)

@admin.register(HelpTopic)
class HelpTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'created_at')
    list_editable = ('order', 'is_active')
    search_fields = ('title',)

@admin.register(HelpTab)
class HelpTabAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'order', 'is_active')
    list_filter = ('topic',)
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'content')