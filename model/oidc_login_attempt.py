from datetime import datetime

from extensions import db


class OidcLoginAttempt(db.Model):
    __tablename__ = 'oidc_login_attempt'

    state_hash = db.Column(db.String(64), primary_key=True)
    code_verifier = db.Column(db.String(128), nullable=False)
    nonce = db.Column(db.String(128), nullable=False)
    target_app = db.Column(db.String(20), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=datetime.utcnow,
    )

