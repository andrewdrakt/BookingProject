from django import template
from datetime import timedelta

register = template.Library()
@register.filter
def duration_pretty(td):
    if not isinstance(td, timedelta):
        return str(td)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    parts = []
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} мин")
    if not parts:
        parts.append("меньше 1 мин")
    return " ".join(parts)