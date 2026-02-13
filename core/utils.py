from datetime import datetime, timedelta
from django.utils import timezone
from calendar import monthrange

def ceil_to_minute(dt):
    """
    Округляет datetime вверх до ближайшей целой минуты.
    Если секунды и микросекунды равны 0, возвращает исходное значение.
    """
    if dt.second == 0 and dt.microsecond == 0:
        return dt
    # Добавляем минуту и вычитаем секунды/микросекунды
    return dt + timedelta(minutes=1) - timedelta(seconds=dt.second, microseconds=dt.microsecond)


def calculate_next_attempt(attempt_number, intervals_dict):
    """
    Возвращает timedelta для следующей попытки.
    Поддерживает ключи как int, так и str.
    """
    minutes = intervals_dict.get(attempt_number)
    if minutes is None:
        minutes = intervals_dict.get(str(attempt_number))
    if minutes is None:
        minutes = 20
    return timedelta(minutes=minutes)


def calc_time_until(dt):
    """
    Возвращает строку с временем до звонка:
    - "Просрочено" если время прошло
    - "Xд Yч" если больше 24 часов
    - "Zч Mм" если меньше 24 часов
    """
    if dt <= timezone.now():
        return "Просрочено"
    
    delta = dt - timezone.now()
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    if days > 0:
        return f"{days}д {hours}ч"
    else:
        if hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"


def calc_notification_status(dt):
    """
    Возвращает статус уведомления:
    - "Просрочено" если время уже наступило
    - "Скоро" если до звонка осталось 5 минут или меньше
    - "Близко" если до звонка осталось от 5 до 15 минут
    - "Запланиран" во всех остальных случаях
    """
    delta = dt - timezone.now()
    if delta.total_seconds() <= 0:
        return "Просрочено"
    if delta.total_seconds() <= 300:  # 5 минут
        return "Скоро"
    if delta.total_seconds() <= 900:  # 15 минут
        return "Близко"
    return "Запланиран"


def generate_work_schedule(year, month, schedule_type, first_work_date=None):
    """
    Генерирует словарь {день: рабочий_ли} для календаря.
    Для графика 2/2 используется непрерывный цикл от first_work_date.
    """
    days_in_month = monthrange(year, month)[1]
    schedule = {}

    if schedule_type == '5/2':
        for d in range(1, days_in_month + 1):
            dt = datetime(year, month, d)
            schedule[d] = dt.weekday() < 5

    elif schedule_type == '2/2':
        if not first_work_date:
            first_work_date = datetime(year, month, 1).date()
        else:
            if isinstance(first_work_date, str):
                first_work_date = datetime.strptime(first_work_date, '%Y-%m-%d').date()

        for d in range(1, days_in_month + 1):
            current_date = datetime(year, month, d).date()
            diff = (current_date - first_work_date).days
            schedule[d] = (diff % 4) in (0, 1)

    else:  # индивидуальный – все дни рабочие
        for d in range(1, days_in_month + 1):
            schedule[d] = True

    return schedule