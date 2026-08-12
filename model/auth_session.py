import uuid
from datetime import datetime

from extensions import db


AUTH_SESSION_ID = db.BigInteger().with_variant(db.Integer, 'sqlite')


class AuthSession(db.Model):
    __tablename__ = 'auth_session'
    __table_args__ = (
        db.Index(
            'idx_auth_session_user_active',
            'user_identity',
            'expires_at',
            postgresql_where=db.text('revoked_at IS NULL'),
        ),
    )

    id = db.Column(AUTH_SESSION_ID, primary_key=True, autoincrement=True)
    session_id = db.Column(
        db.String(36),
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_identity = db.Column(
        db.String(100),
        db.ForeignKey('app_user.username', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    current_refresh_jti = db.Column(db.String(64), nullable=True, unique=True)
    previous_refresh_jti = db.Column(db.String(64), nullable=True)
    refresh_rotated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    last_used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    def revoke(self, revoked_at=None):
        self.revoked_at = revoked_at or datetime.utcnow()
