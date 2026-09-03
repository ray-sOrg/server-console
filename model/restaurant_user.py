"""H5 user mappings, outside console DB metadata."""
from datetime import timezone

import sqlalchemy as sa
from sqlalchemy.orm import deferred

from model.dish import RestaurantBase


class RestaurantUser(RestaurantBase):
    __tablename__ = 'User'

    id = sa.Column(sa.Uuid(as_uuid=False), primary_key=True)
    account = sa.Column(sa.Text, nullable=False)
    passwordHash = deferred(sa.Column(sa.Text, nullable=False), raiseload=True)
    nickname = sa.Column(sa.Text)
    avatar = sa.Column(sa.Text)
    phone = sa.Column(sa.Text)
    gender = sa.Column(sa.String)
    birthday = sa.Column(sa.DateTime)
    bio = sa.Column(sa.String(200))
    role = sa.Column(sa.String, nullable=False)
    createdAt = sa.Column(sa.DateTime)
    updatedAt = sa.Column(sa.DateTime)
    lastLoginAt = sa.Column(sa.DateTime)

    def to_dict(self):
        # Explicit allowlist: never return passwordHash, sessions or login IP.
        result = {
            field: getattr(self, field)
            for field in ('id', 'account', 'nickname', 'avatar', 'phone',
                          'gender', 'bio', 'role')
        }
        for field in ('createdAt', 'updatedAt', 'lastLoginAt'):
            value = getattr(self, field)
            # Prisma stores UTC in PostgreSQL timestamp-without-time-zone.
            result[field] = (
                value.replace(tzinfo=timezone.utc).isoformat() if value else None
            )
        result['birthday'] = self.birthday.date().isoformat() if self.birthday else None
        return result


class RestaurantSession(RestaurantBase):
    __tablename__ = 'Session'

    id = sa.Column(sa.Text, primary_key=True)
    userId = sa.Column(sa.Uuid(as_uuid=False), nullable=False)
    expiresAt = sa.Column(sa.DateTime, nullable=False)


class RestaurantAuthRateLimit(RestaurantBase):
    """Only the key is needed to clear an account's failed login attempts."""
    __tablename__ = 'AuthRateLimit'

    key = sa.Column(sa.String(64), primary_key=True)
