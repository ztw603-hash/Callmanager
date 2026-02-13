from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json

class UserSettings(models.Model):
    SCHEDULE_CHOICES = [
        ('5/2', 'Офисный 5/2'),
        ('2/2', 'Сменный 2/2'),
        ('individual', 'Индивидуальный'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default='5/2')
    first_work_date = models.DateField(null=True, blank=True, verbose_name='Первый рабочий день')
    intervals = models.TextField(default=json.dumps({1: 20, 2: 30, 3: 60, 4: 120, 5: 240}))
    sound_enabled = models.BooleanField(default=True)
    volume = models.PositiveSmallIntegerField(default=100, validators=[MinValueValidator(0), MaxValueValidator(100)])
    dark_theme = models.BooleanField(default=False, verbose_name='Тёмная тема')
    column_widths = models.TextField(default='{}', blank=True)

    def get_intervals_dict(self):
        if not self.intervals:
            return {1: 20, 2: 30, 3: 60, 4: 120, 5: 240}
        raw = self.intervals.strip()
        try:
            str_dict = json.loads(raw)
            return {int(k): v for k, v in str_dict.items()}
        except (json.JSONDecodeError, ValueError, TypeError):
            try:
                fixed = raw.replace("'", '"')
                str_dict = json.loads(fixed)
                return {int(k): v for k, v in str_dict.items()}
            except:
                return {1: 20, 2: 30, 3: 60, 4: 120, 5: 240}

    def save(self, *args, **kwargs):
        if isinstance(self.intervals, dict):
            self.intervals = json.dumps(self.intervals, ensure_ascii=False)
        elif isinstance(self.intervals, str):
            try:
                json.loads(self.intervals)
            except:
                try:
                    fixed = self.intervals.replace("'", '"')
                    json.loads(fixed)
                    self.intervals = fixed
                except:
                    self.intervals = json.dumps({1: 20, 2: 30, 3: 60, 4: 120, 5: 240})
        super().save(*args, **kwargs)


class CallRecord(models.Model):
    CALL_TYPES = [
        ('Недозвон', 'Недозвон'),
        ('Перезвон', 'Перезвон'),
        ('Отслеживание', 'Отслеживание'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='call_records')
    comment = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    first_attempt = models.DateTimeField()
    next_attempt = models.DateTimeField(db_index=True)
    attempt_number = models.PositiveSmallIntegerField(default=1)
    call_type = models.CharField(max_length=20, choices=CALL_TYPES, default='Недозвон')
    notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_attempt']


class TrackingRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracking_records')
    claim = models.CharField(max_length=255, verbose_name='Заявка')
    phone = models.CharField(max_length=50, verbose_name='Телефон', blank=True)  # новое поле
    crm = models.CharField(max_length=100, verbose_name='Номер СРМ')
    connection_datetime = models.DateTimeField(verbose_name='Дата/время подключения')
    call_record = models.OneToOneField(
        CallRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Связанный звонок'
    )
    status = models.CharField(max_length=50, default='Активна', verbose_name='Статус')
    completed = models.BooleanField(default=False, verbose_name='Выполнена')  # новое поле
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.claim} - {self.phone}'


class DailyTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_tasks')
    date = models.DateField(db_index=True)
    task = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['date', 'id']


class Note(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='note')
    content = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class HelpTopic(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название темы')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Справочная тема'
        verbose_name_plural = 'Справочные темы'

    def __str__(self):
        return self.title


class HelpTab(models.Model):
    topic = models.ForeignKey(HelpTopic, on_delete=models.CASCADE, related_name='tabs', verbose_name='Тема')
    title = models.CharField(max_length=200, verbose_name='Название вкладки')
    content = models.TextField(verbose_name='Содержимое')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Вкладка справочника'
        verbose_name_plural = 'Вкладки справочника'

    def __str__(self):
        return f'{self.topic.title} - {self.title}'


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)