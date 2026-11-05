"""Database-backed opaque sessions and one-use password recovery."""
import hashlib
import logging
import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))
COOKIE = "watchdemo_session"
router = APIRouter(prefix="/auth")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def verify(encoded, password):
    try:
        return HASHER.verify(encoded, password)
    except VerificationError:
        return False


def session(request: Request):
    token = request.cookies.get(COOKIE, "")
    with request.app.state.repository.connect() as conn:
        return conn.execute("""SELECT s.*, u.email, u.display_name FROM sessions s
            LEFT JOIN users u ON u.id = s.user_id
            WHERE token_hash = %s AND expires_at > now()""", (digest(token),)).fetchone()


def current_user(request: Request):
    row = session(request)
    if row is None or row["user_id"] is None:
        raise HTTPException(401, "Войдите в аккаунт")
    return row


def csrf(request: Request):
    # Reject untrusted browser origins even when a token was somehow obtained.
    origin = request.headers.get("origin")
    if origin is not None and origin not in request.app.state.origins:
        raise HTTPException(403, "Недопустимый Origin")
    row = session(request)
    if row is None or not secrets.compare_digest(
        row["csrf_token"].encode("utf-8"), request.headers.get("x-csrf-token", "").encode("utf-8")
    ):
        raise HTTPException(403, "Обновите страницу: неверный CSRF-токен")
    return row


def public(row):
    return {"id": row["user_id"], "email": row["email"], "display_name": row["display_name"]}


def new_session(conn, user_id, response, old_token=""):
    token, csrf_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    conn.execute("DELETE FROM sessions WHERE token_hash = %s", (digest(old_token),))
    conn.execute("""INSERT INTO sessions VALUES (%s, %s, %s, now() + interval '7 days')""",
                 (digest(token), user_id, csrf_token))
    response.set_cookie(COOKIE, token, httponly=True, secure=os.getenv("WATCHDEMO_COOKIE_SECURE", "true").lower() == "true",
                        samesite="lax", max_age=604800, path="/")
    return csrf_token


def limited(request, action, maximum=20):
    key = digest(action + ":" + (request.client.host if request.client else "unknown"))
    with request.app.state.repository.connect() as conn:
        count = conn.execute("""INSERT INTO auth_limits VALUES (%s, 1, now() + interval '15 minutes')
            ON CONFLICT (key) DO UPDATE SET
                attempts = CASE WHEN auth_limits.expires_at < now() THEN 1 ELSE auth_limits.attempts + 1 END,
                expires_at = CASE WHEN auth_limits.expires_at < now() THEN now() + interval '15 minutes' ELSE auth_limits.expires_at END
            RETURNING attempts""", (key,)).fetchone()["attempts"]
    return count > maximum


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Registration(Credentials):
    display_name: str = Field(min_length=1, max_length=80, pattern=r"\S")


class Profile(BaseModel):
    display_name: str = Field(min_length=1, max_length=80, pattern=r"\S")


class PasswordChange(BaseModel):
    old_password: str = Field(max_length=128)
    password: str = Field(min_length=12, max_length=128)


class Recovery(BaseModel):
    email: EmailStr


class Reset(BaseModel):
    token: str = Field(min_length=20, max_length=128)
    password: str = Field(min_length=12, max_length=128)


@router.get("/session")
def get_session(request: Request, response: Response):
    row = session(request)
    response.headers["Cache-Control"] = "no-store"
    if row:
        return {"user": public(row) if row["user_id"] else None, "csrf_token": row["csrf_token"]}
    with request.app.state.repository.connect() as conn:
        token = new_session(conn, None, response, request.cookies.get(COOKIE, ""))
    return {"user": None, "csrf_token": token}


@router.post("/register", dependencies=[Depends(csrf)])
def register(body: Registration, request: Request):
    if limited(request, "register"):
        raise HTTPException(429, "Повторите позже")
    encoded = HASHER.hash(body.password)
    with request.app.state.repository.connect() as conn:
        row = conn.execute("""INSERT INTO users VALUES (%s, %s, %s, %s, now())
            ON CONFLICT(email) DO NOTHING RETURNING id""",
                           (uuid4(), str(body.email).lower(), body.display_name.strip(), encoded)).fetchone()
    if row is None:
        raise HTTPException(409, "Регистрация недоступна для этого email")
    return {"message": "Аккаунт создан. Войдите в систему."}


@router.post("/login", dependencies=[Depends(csrf)])
def login(body: Credentials, request: Request, response: Response):
    if limited(request, "login"):
        raise HTTPException(429, "Повторите позже")
    with request.app.state.repository.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = %s FOR UPDATE", (str(body.email).lower(),)).fetchone()
        if not verify(row["password_hash"] if row else DUMMY_HASH, body.password):
            raise HTTPException(401, "Неверный email или пароль")
        token = new_session(conn, row["id"], response, request.cookies.get(COOKIE, ""))
    return {"user": {"id": row["id"], "email": row["email"], "display_name": row["display_name"]}, "csrf_token": token}


@router.post("/logout", dependencies=[Depends(csrf)])
def logout(request: Request, response: Response):
    with request.app.state.repository.connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = %s", (digest(request.cookies.get(COOKIE, "")),))
    response.delete_cookie(COOKIE, path="/")
    return {"message": "Вы вышли"}


@router.get("/profile")
def profile(user=Depends(current_user)):
    return public(user)


@router.patch("/profile", dependencies=[Depends(csrf)])
def update_profile(body: Profile, request: Request, user=Depends(current_user)):
    with request.app.state.repository.connect() as conn:
        conn.execute("UPDATE users SET display_name = %s WHERE id = %s", (body.display_name.strip(), user["user_id"]))
    return {"message": "Профиль обновлён"}


def replace_password(conn, user_id, encoded):
    conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (encoded, user_id))
    conn.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
    conn.execute("UPDATE password_resets SET used_at = now() WHERE user_id = %s AND used_at IS NULL", (user_id,))


@router.post("/password", dependencies=[Depends(csrf)])
def change_password(body: PasswordChange, request: Request, response: Response, user=Depends(current_user)):
    if limited(request, "password"):
        raise HTTPException(429, "Повторите позже")
    encoded = HASHER.hash(body.password)
    with request.app.state.repository.connect() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = %s FOR UPDATE", (user["user_id"],)).fetchone()
        if not verify(row["password_hash"], body.old_password):
            raise HTTPException(400, "Неверный текущий пароль")
        replace_password(conn, user["user_id"], encoded)
    response.delete_cookie(COOKIE, path="/")
    return {"message": "Пароль изменён. Войдите повторно на всех устройствах."}


def send_recovery(email, token):
    try:
        message = EmailMessage()
        message["From"] = os.getenv("WATCHDEMO_SMTP_FROM", "watchdemo@localhost")
        message["To"] = email
        message["Subject"] = "WatchDemo: восстановление пароля"
        # Fragment keeps the secret out of web server access logs/referrer URLs.
        message.set_content("Ссылка действует 30 минут:\n" + os.getenv("WATCHDEMO_FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/") + "/reset-password#" + token)
        mode = os.getenv("WATCHDEMO_SMTP_TLS", "starttls")
        smtp_class = smtplib.SMTP_SSL if mode == "ssl" else smtplib.SMTP
        with smtp_class(os.getenv("WATCHDEMO_SMTP_HOST", "127.0.0.1"), int(os.getenv("WATCHDEMO_SMTP_PORT", "1025")), timeout=10) as smtp:
            if mode == "starttls":
                smtp.starttls(context=ssl.create_default_context())
            if os.getenv("WATCHDEMO_SMTP_USER"):
                smtp.login(os.environ["WATCHDEMO_SMTP_USER"], os.environ["WATCHDEMO_SMTP_PASSWORD"])
            smtp.send_message(message)
    except Exception:
        # No email, SMTP credentials or reset links in logs or HTTP responses.
        logging.getLogger(__name__).error("Recovery mail delivery failed")


@router.post("/forgot-password", dependencies=[Depends(csrf)])
def forgot(body: Recovery, request: Request, tasks: BackgroundTasks):
    message = {"message": "Если аккаунт существует, ссылка для восстановления отправлена."}
    if limited(request, "forgot", 5):
        return message
    with request.app.state.repository.connect() as conn:
        row = conn.execute("SELECT id, email FROM users WHERE email = %s FOR UPDATE", (str(body.email).lower(),)).fetchone()
        if row:
            token = secrets.token_urlsafe(32)
            conn.execute("UPDATE password_resets SET used_at = now() WHERE user_id = %s AND used_at IS NULL", (row["id"],))
            conn.execute("INSERT INTO password_resets VALUES (%s, %s, now() + interval '30 minutes', NULL)", (digest(token), row["id"]))
            tasks.add_task(send_recovery, row["email"], token)
    return message


@router.post("/reset-password", dependencies=[Depends(csrf)])
def reset(body: Reset, request: Request, response: Response):
    if limited(request, "reset"):
        raise HTTPException(429, "Повторите позже")
    encoded = HASHER.hash(body.password)
    with request.app.state.repository.connect() as conn:
        # Lock the user first, consistently with change/forgot/login operations.
        row = conn.execute("""SELECT u.id FROM users u JOIN password_resets r ON r.user_id = u.id
            WHERE r.token_hash = %s FOR UPDATE OF u""", (digest(body.token),)).fetchone()
        valid = conn.execute("""SELECT user_id FROM password_resets WHERE token_hash = %s
            AND used_at IS NULL AND expires_at > now()""", (digest(body.token),)).fetchone()
        if not row or not valid:
            raise HTTPException(400, "Ссылка недействительна или истекла")
        replace_password(conn, row["id"], encoded)
    response.delete_cookie(COOKIE, path="/")
    return {"message": "Пароль восстановлен. Войдите с новым паролем."}
