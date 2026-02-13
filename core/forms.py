from django import forms
from .models import CallRecord, TrackingRecord, DailyTask, UserSettings

class CallRecordForm(forms.ModelForm):
    next_attempt = forms.DateTimeField(
        input_formats=['%Y-%m-%d %H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        required=False
    )
    class Meta:
        model = CallRecord
        fields = ['comment', 'phone', 'next_attempt', 'call_type']
        widgets = {
            'comment': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'call_type': forms.Select(attrs={'class': 'form-select'}),
        }

class TrackingForm(forms.ModelForm):
    connection_datetime = forms.DateTimeField(
        input_formats=['%Y-%m-%d %H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
    )
    class Meta:
        model = TrackingRecord
        fields = ['claim', 'phone', 'crm', 'connection_datetime']  # добавлено поле phone
        widgets = {
            'claim': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '8XXXXXXXXXX'}),
            'crm': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DailyTaskForm(forms.ModelForm):
    class Meta:
        model = DailyTask
        fields = ['task']
        widgets = {
            'task': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Новая задача'})
        }

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['schedule_type', 'first_work_date', 'sound_enabled', 'volume', 'dark_theme']
        widgets = {
            'schedule_type': forms.Select(attrs={'class': 'form-select'}),
            'first_work_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'sound_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'volume': forms.NumberInput(attrs={'class': 'form-control', 'type': 'range', 'min': 0, 'max': 100}),
            'dark_theme': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }