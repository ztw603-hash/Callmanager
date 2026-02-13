import json
import re
from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required

from .models import *
from .forms import *
from .utils import *


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_user_settings(user):
    settings, created = UserSettings.objects.get_or_create(user=user)
    return settings


def parse_datetime(dt_str):
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    dt_str = dt_str[:19]
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M',
                '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            naive_dt = datetime.strptime(dt_str, fmt)
            return timezone.make_aware(naive_dt, timezone.get_default_timezone())
        except ValueError:
            continue
    raise ValueError(f'Неверный формат даты/времени: {dt_str}')


def ceil_to_minute(dt):
    if dt.second == 0 and dt.microsecond == 0:
        return dt
    return dt + timedelta(minutes=1) - timedelta(seconds=dt.second, microseconds=dt.microsecond)


# ========== ГЛАВНАЯ СТРАНИЦА ==========

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


# ========== ЗАГРУЗКА ВКЛАДОК ==========

@login_required
def tab_calls(request):
    return render(request, 'includes/tab_calls.html')


@login_required
def tab_settings(request):
    return render(request, 'includes/tab_settings.html')


@login_required
def tab_schedule(request):
    return render(request, 'includes/tab_schedule.html')


@login_required
def tab_notes(request):
    return render(request, 'includes/tab_notes.html')


@login_required
def tab_tracking(request):
    return render(request, 'includes/tab_tracking.html')


# ========== ЗАПИСИ ЗВОНКОВ ==========

@login_required
def get_calls(request):
    filter_date = request.GET.get('date', '')
    calls = CallRecord.objects.filter(user=request.user)
    if filter_date:
        calls = calls.filter(next_attempt__date=filter_date)
    data = []
    for c in calls:
        rounded_next = ceil_to_minute(c.next_attempt)
        first_local = timezone.localtime(c.first_attempt)
        next_local = timezone.localtime(rounded_next)
        data.append({
            'id': c.id,
            'comment': c.comment,
            'phone': c.phone,
            'first_attempt': first_local.strftime('%Y-%m-%d %H:%M'),
            'next_attempt': next_local.strftime('%Y-%m-%d %H:%M'),
            'attempt_number': c.attempt_number,
            'time_until': calc_time_until(rounded_next),
            'notification_status': calc_notification_status(rounded_next),
            'call_type': c.call_type,
        })
    return JsonResponse({'calls': data})


@login_required
@require_POST
def add_call(request):
    user = request.user
    settings = get_user_settings(user)

    comment = request.POST.get('comment')
    phone = request.POST.get('phone')
    next_attempt_str = request.POST.get('next_attempt')
    call_type = request.POST.get('call_type', 'Недозвон')

    if not comment or not phone:
        return HttpResponseBadRequest('Заполните все поля')

    now = timezone.now()

    if call_type == 'Недозвон' or not next_attempt_str:
        intervals = settings.get_intervals_dict()
        delta = calculate_next_attempt(1, intervals)
        next_attempt = ceil_to_minute(now + delta)
    else:
        try:
            next_attempt = parse_datetime(next_attempt_str)
            next_attempt = ceil_to_minute(next_attempt)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

    call = CallRecord.objects.create(
        user=user,
        comment=comment,
        phone=phone,
        first_attempt=now,
        next_attempt=next_attempt,
        attempt_number=1,
        call_type=call_type
    )
    return JsonResponse({'status': 'ok', 'id': call.id})


@login_required
@require_POST
def update_call_time(request):
    call_id = request.POST.get('id')
    call = get_object_or_404(CallRecord, id=call_id, user=request.user)
    settings = get_user_settings(request.user)
    new_attempt = call.attempt_number + 1
    delta = calculate_next_attempt(new_attempt, settings.get_intervals_dict())
    call.next_attempt = ceil_to_minute(timezone.now() + delta)
    call.attempt_number = new_attempt
    call.call_type = 'Перезвон'
    call.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def adjust_call_time(request):
    call_id = request.POST.get('id')
    new_time_str = request.POST.get('next_attempt')
    call = get_object_or_404(CallRecord, id=call_id, user=request.user)
    try:
        next_attempt = parse_datetime(new_time_str)
        next_attempt = ceil_to_minute(next_attempt)
    except ValueError as e:
        return HttpResponseBadRequest(str(e))
    call.next_attempt = next_attempt
    call.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def delete_calls(request):
    ids = request.POST.getlist('ids[]')
    calls = CallRecord.objects.filter(id__in=ids, user=request.user)
    for call in calls:
        try:
            tracking = TrackingRecord.objects.get(call_record=call)
            tracking.delete()  # удаляем заявку вместе со звонком
        except TrackingRecord.DoesNotExist:
            pass
    calls.delete()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def postpone_call(request):
    call_id = request.POST.get('id')
    call = get_object_or_404(CallRecord, id=call_id, user=request.user)
    call.next_attempt = ceil_to_minute(call.next_attempt + timedelta(minutes=10))
    call.save(update_fields=['next_attempt'])
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def complete_call(request):
    """Отметить звонок как успешный: удалить звонок, пометить заявку выполненной."""
    call_id = request.POST.get('id')
    call = get_object_or_404(CallRecord, id=call_id, user=request.user)
    try:
        tracking = TrackingRecord.objects.get(call_record=call)
        tracking.completed = True
        tracking.call_record = None
        tracking.status = 'Выполнена'
        tracking.save()
    except TrackingRecord.DoesNotExist:
        pass
    call.delete()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def clear_all_records(request):
    user = request.user
    CallRecord.objects.filter(user=user).delete()
    TrackingRecord.objects.filter(user=user).delete()
    return JsonResponse({'status': 'ok', 'message': 'Все записи очищены'})


@login_required
@require_POST
def update_call_comment(request):
    call_id = request.POST.get('id')
    comment = request.POST.get('comment')
    if not comment:
        return HttpResponseBadRequest('Комментарий не может быть пустым')
    call = get_object_or_404(CallRecord, id=call_id, user=request.user)
    call.comment = comment
    call.save(update_fields=['comment'])
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def update_call_phone(request):
    call_id = request.POST.get('id')
    phone = request.POST.get('phone')
    if not phone:
        return HttpResponseBadRequest('Телефон не может быть пустым')

    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        digits = '8' + digits
    elif len(digits) == 11 and digits[0] == '7':
        digits = '8' + digits[1:]
    elif len(digits) == 11 and digits[0] == '8':
        digits = digits
    else:
        return HttpResponseBadRequest('Неверный формат телефона (должно быть 10 или 11 цифр)')

    call = get_object_or_404(CallRecord, id=call_id, user=request.user)
    call.phone = digits
    call.save(update_fields=['phone'])
    return JsonResponse({'status': 'ok'})


# ========== ОТСЛЕЖИВАНИЕ ЗАЯВОК ==========

@login_required
def get_tracking(request):
    tracking = TrackingRecord.objects.filter(user=request.user)
    data = []
    for t in tracking:
        conn_local = timezone.localtime(t.connection_datetime)
        data.append({
            'tracking_id': t.id,
            'claim': t.claim,
            'phone': t.phone,
            'crm': t.crm,
            'connection_datetime': conn_local.strftime('%Y-%m-%d %H:%M'),
            'call_record_id': t.call_record_id if t.call_record else None,
            'status': t.status,
            'completed': t.completed,
        })
    return JsonResponse({'tracking': data})


@login_required
@require_POST
def add_tracking(request):
    user = request.user

    claim = request.POST.get('claim')
    phone = request.POST.get('phone')
    crm = request.POST.get('crm')
    connection_datetime_str = request.POST.get('connection_datetime')

    if not claim or not phone or not crm or not connection_datetime_str:
        return HttpResponseBadRequest('Заполните все поля')

    try:
        connection_dt = parse_datetime(connection_datetime_str)
    except ValueError as e:
        return HttpResponseBadRequest(str(e))

    tracking = TrackingRecord.objects.create(
        user=user,
        claim=claim,
        phone=phone,
        crm=crm,
        connection_datetime=connection_dt,
        status='Активна',
        completed=False
    )

    next_time = ceil_to_minute(connection_dt + timedelta(hours=1))

    call = CallRecord.objects.create(
        user=user,
        comment=f"Заявка: {claim}",
        phone=phone,  # ✅ теперь используем телефон из заявки
        first_attempt=timezone.now(),
        next_attempt=next_time,
        attempt_number=1,
        call_type='Отслеживание'
    )

    tracking.call_record = call
    tracking.save()

    return JsonResponse({'status': 'ok', 'tracking_id': tracking.id, 'call_id': call.id})


@login_required
@require_POST
def delete_tracking(request):
    ids = request.POST.getlist('ids[]')
    for tid in ids:
        tracking = get_object_or_404(TrackingRecord, id=tid, user=request.user)
        if tracking.call_record:
            tracking.call_record.delete()
        tracking.delete()
    return JsonResponse({'status': 'ok'})


# ========== КАЛЕНДАРЬ И ЗАДАЧИ ==========

@login_required
def get_schedule_data(request):
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    settings = get_user_settings(request.user)

    work_schedule = generate_work_schedule(
        year, month,
        settings.schedule_type,
        settings.first_work_date
    )

    tasks = DailyTask.objects.filter(user=request.user, date__year=year, date__month=month)
    tasks_by_day = {}
    for t in tasks:
        day = t.date.day
        if day not in tasks_by_day:
            tasks_by_day[day] = []
        tasks_by_day[day].append({'id': t.id, 'task': t.task, 'completed': t.completed})

    return JsonResponse({
        'work_schedule': work_schedule,
        'tasks': tasks_by_day
    })


@login_required
@require_POST
def add_task(request):
    user = request.user
    date_str = request.POST.get('date')
    task_text = request.POST.get('task')
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    task = DailyTask.objects.create(user=user, date=date, task=task_text)
    return JsonResponse({'id': task.id, 'task': task.task, 'completed': task.completed})


@login_required
@require_POST
def toggle_task(request):
    task_id = request.POST.get('id')
    task = get_object_or_404(DailyTask, id=task_id, user=request.user)
    task.completed = not task.completed
    task.save()
    return JsonResponse({'completed': task.completed})


@login_required
@require_POST
def delete_task(request):
    task_id = request.POST.get('id')
    DailyTask.objects.filter(id=task_id, user=request.user).delete()
    return JsonResponse({'status': 'ok'})


# ========== ЗАМЕТКИ ==========

@login_required
def get_note(request):
    note, _ = Note.objects.get_or_create(user=request.user)
    return JsonResponse({'content': note.content})


@login_required
@require_POST
def save_note(request):
    content = request.POST.get('content', '')
    note, _ = Note.objects.get_or_create(user=request.user)
    note.content = content
    note.save()
    return JsonResponse({'status': 'ok'})


# ========== НАСТРОЙКИ ==========

@login_required
def get_settings(request):
    settings = get_user_settings(request.user)
    return JsonResponse({
        'schedule_type': settings.schedule_type,
        'first_work_date': settings.first_work_date.isoformat() if settings.first_work_date else None,
        'intervals': settings.get_intervals_dict(),
        'sound_enabled': settings.sound_enabled,
        'volume': settings.volume,
        'dark_theme': settings.dark_theme,
    })


@login_required
@require_POST
def save_settings(request):
    user = request.user
    settings = get_user_settings(user)

    settings.schedule_type = request.POST.get('schedule_type', settings.schedule_type)

    first_work_date_str = request.POST.get('first_work_date')
    if first_work_date_str and first_work_date_str.strip():
        try:
            settings.first_work_date = datetime.strptime(first_work_date_str.strip(), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            settings.first_work_date = None
    else:
        settings.first_work_date = None

    settings.sound_enabled = request.POST.get('sound_enabled') == 'true'
    settings.volume = int(request.POST.get('volume', settings.volume))
    settings.dark_theme = request.POST.get('dark_theme') == 'true'

    intervals_json = request.POST.get('intervals')
    if intervals_json:
        try:
            intervals = json.loads(intervals_json)
            settings.intervals = json.dumps(intervals, ensure_ascii=False)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Неверный формат интервалов'}, status=400)

    settings.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def reset_settings(request):
    user = request.user
    settings = get_user_settings(user)
    settings.schedule_type = '5/2'
    settings.first_work_date = None
    settings.intervals = json.dumps({1: 20, 2: 30, 3: 60, 4: 120, 5: 240})
    settings.sound_enabled = True
    settings.volume = 100
    settings.dark_theme = False
    settings.save()
    return JsonResponse({'status': 'ok'})


# ========== УВЕДОМЛЕНИЯ ==========

@login_required
def get_notifications(request):
    user = request.user
    now = timezone.now()

    calls = CallRecord.objects.filter(
        user=user,
        notified_at__isnull=True
    )

    data = []
    for call in calls:
        rounded_next = ceil_to_minute(call.next_attempt)
        if rounded_next <= now:
            next_local = timezone.localtime(rounded_next)
            data.append({
                'id': call.id,
                'comment': call.comment,
                'phone': call.phone,
                'next_attempt': next_local.strftime('%H:%M'),
                'call_type': call.call_type,
            })
            call.notified_at = now
            call.save(update_fields=['notified_at'])

    return JsonResponse({'notifications': data})


# ========== АДМИН-ПАНЕЛЬ (ПОЛЬЗОВАТЕЛИ) ==========

@staff_member_required
def admin_panel(request):
    users = User.objects.all()
    return render(request, 'admin_panel.html', {'users': users})


@staff_member_required
@require_POST
def admin_add_user(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    if not username or not password:
        return HttpResponseBadRequest('Не указан логин или пароль')
    if User.objects.filter(username=username).exists():
        return HttpResponseBadRequest('Пользователь с таким логином уже существует')
    user = User.objects.create_user(username=username, password=password)
    return JsonResponse({'status': 'ok', 'user_id': user.id})


@staff_member_required
@require_POST
def admin_delete_user(request):
    user_id = request.POST.get('user_id')
    if str(user_id) == str(request.user.id):
        return HttpResponseBadRequest('Нельзя удалить себя')
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return JsonResponse({'status': 'ok'})
    except User.DoesNotExist:
        return HttpResponseBadRequest('Пользователь не найден')


# ========== СПРАВОЧНИК ==========

@login_required
def help_index(request):
    topics = HelpTopic.objects.filter(is_active=True).prefetch_related('tabs').order_by('order')
    return render(request, 'help/index.html', {'topics': topics})


@staff_member_required
def admin_help_topics(request):
    topics = HelpTopic.objects.all().prefetch_related('tabs').order_by('order')
    return render(request, 'help/admin_topics.html', {'topics': topics})


@staff_member_required
@require_POST
def admin_add_topic(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        title = data.get('title')
        if not title:
            return HttpResponseBadRequest('Название не может быть пустым')
        HelpTopic.objects.create(title=title)
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return HttpResponseBadRequest(str(e))


@staff_member_required
@require_POST
def admin_edit_topic(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        topic_id = data.get('id')
        title = data.get('title')
        order = data.get('order')
        is_active = data.get('is_active')
        topic = get_object_or_404(HelpTopic, id=topic_id)
        if title:
            topic.title = title
        if order is not None:
            topic.order = int(order)
        if is_active is not None:
            topic.is_active = is_active
        topic.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return HttpResponseBadRequest(str(e))


@staff_member_required
@require_POST
def admin_delete_topic(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        topic_id = data.get('id')
        HelpTopic.objects.filter(id=topic_id).delete()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return HttpResponseBadRequest(str(e))


@staff_member_required
@require_POST
def admin_add_tab(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        topic_id = data.get('topic_id')
        title = data.get('title')
        content = data.get('content')
        if not title or not content or not topic_id:
            return HttpResponseBadRequest('Заполните все поля')
        topic = get_object_or_404(HelpTopic, id=topic_id)
        HelpTab.objects.create(topic=topic, title=title, content=content)
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return HttpResponseBadRequest(str(e))


@staff_member_required
@require_POST
def admin_edit_tab(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        tab_id = data.get('id')
        title = data.get('title')
        content = data.get('content')
        order = data.get('order')
        is_active = data.get('is_active')
        tab = get_object_or_404(HelpTab, id=tab_id)
        if title:
            tab.title = title
        if content:
            tab.content = content
        if order is not None:
            tab.order = int(order)
        if is_active is not None:
            tab.is_active = is_active
        tab.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return HttpResponseBadRequest(str(e))


@staff_member_required
@require_POST
def admin_delete_tab(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        tab_id = data.get('id')
        HelpTab.objects.filter(id=tab_id).delete()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return HttpResponseBadRequest(str(e))