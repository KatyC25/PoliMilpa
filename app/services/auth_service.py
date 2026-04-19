import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import jwt
from passlib.context import CryptContext

from app.db import SessionLocal, init_db
from app.models import LoginAudit, User


@dataclass(frozen=True)
class UserIdentity:
    username: str
    role: str
    full_name: str


class AuthService:
    def __init__(self) -> None:
        self.secret_key = os.getenv(
            "JWT_SECRET_KEY",
            "polimilpa-dev-secret-change-this-key-min-32",
        )
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.exp_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self._pwd_context = CryptContext(
            schemes=["pbkdf2_sha256"],
            deprecated="auto",
        )
        init_db()
        self._seed_users_if_needed()

    def _load_bootstrap_users(self) -> Dict[str, Dict[str, str]]:
        users_json = os.getenv("POLIMILPA_USERS_JSON") or os.getenv("AGRONI_USERS_JSON")
        if users_json:
            try:
                loaded = json.loads(users_json)
                if isinstance(loaded, dict):
                    return loaded
            except json.JSONDecodeError:
                pass

        return {
            "superadmin": {
                "password": "superadmin123",
                "role": "superadmin",
                "full_name": "Super Administrador",
            },
            "admin": {
                "password": "admin123",
                "role": "admin",
                "full_name": "Administrador",
            },
            "tecnico": {
                "password": "tecnico123",
                "role": "tecnico",
                "full_name": "Tecnico",
            },
        }

    def _seed_users_if_needed(self) -> None:
        users = self._load_bootstrap_users()
        db = SessionLocal()
        try:
            for username, data in users.items():
                existing = db.query(User).filter(User.username == username).first()
                if existing:
                    continue
                password = str(data.get("password", ""))
                if not password:
                    continue
                user = User(
                    username=username,
                    password_hash=self._pwd_context.hash(password),
                    role=str(data.get("role", "tecnico")),
                    full_name=str(data.get("full_name", username)),
                    is_active=True,
                )
                db.add(user)
            db.commit()
        finally:
            db.close()

    def _log_login_attempt(
        self,
        username: str,
        success: bool,
        reason: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> None:
        db = SessionLocal()
        try:
            audit = LoginAudit(
                username=username,
                success=success,
                reason=reason,
                ip_address=(ip_address or "")[:100],
                user_agent=(user_agent or "")[:500],
            )
            db.add(audit)
            db.commit()
        finally:
            db.close()

    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[UserIdentity]:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
        finally:
            db.close()

        if user is None:
            self._log_login_attempt(
                username=username,
                success=False,
                reason="user_not_found",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return None
        if not user.is_active:
            self._log_login_attempt(
                username=username,
                success=False,
                reason="user_inactive",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return None
        if not self._pwd_context.verify(password, user.password_hash):
            self._log_login_attempt(
                username=username,
                success=False,
                reason="invalid_password",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return None

        self._log_login_attempt(
            username=username,
            success=True,
            reason="login_ok",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return UserIdentity(
            username=username,
            role=user.role,
            full_name=user.full_name,
        )

    def create_access_token(self, identity: UserIdentity) -> str:
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            minutes=self.exp_minutes
        )
        payload = {
            "sub": identity.username,
            "role": identity.role,
            "full_name": identity.full_name,
            "exp": expires_at,
            "iat": dt.datetime.now(dt.timezone.utc),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> UserIdentity:
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
        )
        username = payload.get("sub")
        role = payload.get("role")
        full_name = payload.get("full_name")
        if not username or not role:
            raise ValueError("Token invalido")
        return UserIdentity(
            username=str(username),
            role=str(role),
            full_name=str(full_name or username),
        )

    @staticmethod
    def has_required_role(user_role: str, allowed_roles: Iterable[str]) -> bool:
        return user_role in set(allowed_roles)
