from datetime import datetime, timedelta, timezone


ACCESS_TOKEN_LIFETIME = timedelta(days=7)
REFRESH_TOKEN_LIFETIME = timedelta(days=180)
REFRESH_ROTATION_GRACE = timedelta(seconds=30)


def utc_now():
    return datetime.now(timezone.utc)


def ensure_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def session_remaining(session, now=None):
    current_time = now or utc_now()
    return ensure_utc(session.expires_at) - current_time


def session_is_active(session, now=None):
    if not session or session.revoked_at is not None:
        return False
    return session_remaining(session, now).total_seconds() > 0


def refresh_jti_is_valid(session, refresh_jti, now=None):
    if refresh_jti == session.current_refresh_jti:
        return True
    rotated_at = ensure_utc(session.refresh_rotated_at)
    if not rotated_at or refresh_jti != session.previous_refresh_jti:
        return False
    current_time = now or utc_now()
    return current_time - rotated_at <= REFRESH_ROTATION_GRACE


def max_age_seconds(duration):
    return max(1, int(duration.total_seconds()))

