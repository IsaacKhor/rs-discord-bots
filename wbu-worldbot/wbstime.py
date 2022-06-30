import math, pytz, inspect
from datetime import datetime, timezone, timedelta

WBS_TIME_DB = {
    0: [2, 9, 16, 23],
    1: [6, 13, 20],
    2: [3, 10, 17],
    3: [0, 7, 14, 21],
    4: [4, 11, 18],
    5: [1, 8, 15, 22],
    6: [5, 12, 19],
}

def get_utctime():
    return datetime.now().astimezone(timezone.utc)

def get_next_wave_datetime(current: datetime):
    """ Get next wave's datetime relative to the current time specified in args. """
    cur = current.astimezone(timezone.utc)
    day = cur.weekday()
    waves_today = WBS_TIME_DB[day]

    next_wave = None

    # Find the hour after the current one
    for wh in waves_today:
        actual_dt = cur.replace(hour=wh, minute=0, second=0, microsecond=0)
        if actual_dt > cur:
            return actual_dt

    # Next wave is tomorrow since we didn't find an hour
    if next_wave == None:
        tmr_weekday = (day + 1) % 7
        hr = WBS_TIME_DB[tmr_weekday][0]

        tomorrow = cur + timedelta(days=1)
        return tomorrow.replace(hour=hr, minute=0, second=0, microsecond=0)


def next_wave_info():
    cur = get_utctime()
    next_wave = get_next_wave_datetime(cur)

    deltasecs = (next_wave - cur).seconds
    deltahr = math.floor(deltasecs / 3600.0)
    deltamins = math.floor((deltasecs % 3600) / 60.0)

    TIME_FORMAT = '%H:00'
    n = next_wave

    def intz(time, zonename):
        return time.astimezone(pytz.timezone(zonename)).strftime(TIME_FORMAT)

    return inspect.cleandoc(
        f"""
        {deltahr}:{deltamins:02} until the next wave.

        Next wave is at:
        {intz(n, 'US/Eastern')} in US/Eastern
        {intz(n, 'US/Central')} in US/Central
        {intz(n, 'US/Pacific')} in US/Pacific
        {intz(n, 'Europe/Paris')} in EU/Central
        {intz(n, 'Europe/Sofia')} in EU/Eastern
        {intz(n, 'Europe/London')} in UK
        {intz(n, 'Singapore')} in UTC+8
        {intz(n, 'Australia/Melbourne')} in Australia/Eastern
        """)


def time_to_next_wave(current=None):
    """
    Calculates `timedelta` to next wave relative to `current` datetime.
    Wave is relative to `current`, `delta` is relative to actual current time
    `current` must be a tz-unaware datetime in UTC
    """
    now = datetime.now().astimezone(timezone.utc)
    if not current:
        current = now
    
    next_wave = get_next_wave_datetime(current)
    return next_wave, next_wave - now