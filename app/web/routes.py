import smtplib
import ssl

from email.message import EmailMessage
from io import BytesIO

from pathlib import Path

from tempfile import NamedTemporaryFile

from time import perf_counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.templating import Jinja2Templates

from pydantic import ValidationError
from PIL import Image, UnidentifiedImageError

from sqlalchemy.orm import Session

from app.auth.dependencies import AUTH_COOKIE_NAME
from app.core.config import settings
from app.auth.security import create_access_token, decode_access_token
from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.coordinator.semantic_check_coordinator import SemanticCheckCoordinator
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.db.models import UserORM
from app.db.session import get_db
from app.reports.report_builder import ReportBuilder
from app.schemas.auth import (
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    UserCreateRequest,
)
from app.schemas.common import StorageMode
from app.services.document_processing_service import DocumentProcessingService
from app.services.password_reset_email_service import PasswordResetEmailService
from app.services.password_reset_link_service import build_password_reset_url
from app.services.password_reset_service import PasswordResetService
from app.services.report_storage_service import ReportStorageService
from app.services.user_service import UserService
from app.services.rag_index_service import RagIndexService
from app.services.rag_source_service import RagSourceService

from datetime import datetime, timedelta, timezone


logger = get_logger(__name__)

router = APIRouter(prefix="/web", tags=["web"])
templates = Jinja2Templates(directory="app/web/templates")

def _value(value):
    return getattr(value, "value", value)


def _format_display_datetime(value) -> str:
    if value is None:
        return "—"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value

    if not isinstance(value, datetime):
        return str(value)

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    local_value = value.astimezone()
    now = datetime.now(local_value.tzinfo)

    if local_value.date() == now.date():
        return f"Сегодня, в {local_value:%H:%M}"

    if local_value.date() == (now - timedelta(days=1)).date():
        return f"Вчера, в {local_value:%H:%M}"

    return local_value.strftime("%d.%m.%Y, %H:%M")

def _datetime_iso(value) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return ""

    if not isinstance(value, datetime):
        return ""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat()

def _report_status_label(value) -> str:
    value = str(_value(value))

    return {
        "ready": "Готов",
        "requires_revision": "Требует доработки",
        "failed": "Ошибка проверки",
        "draft": "Черновик",
    }.get(value, value)


def _source_type_label(value) -> str:
    value = str(_value(value))

    return {
        "vacancy": "Вакансия",
        "requirements": "Требования",
        "checklist": "Чек-лист",
        "policy": "Регламент",
        "other": "Другое",
    }.get(value, value)


def _role_label(value) -> str:
    value = str(_value(value))

    return {
        "candidate": "Кандидат",
        "hr": "HR-специалист",
        "admin": "Администратор",
    }.get(value, value)


templates.env.filters["display_datetime"] = _format_display_datetime
templates.env.filters["report_status_label"] = _report_status_label
templates.env.filters["source_type_label"] = _source_type_label
templates.env.filters["role_label"] = _role_label
templates.env.filters["datetime_iso"] = _datetime_iso

def _localize_web_error(error: Exception) -> str:
    message = str(error)

    translations = {
        "User with this email already exists.": "Пользователь с таким email уже существует.",
        "Admin user cannot be created through public registration.": (
            "Администратора нельзя создать через публичную регистрацию."
        ),
    }

    return translations.get(message, message)

def _get_optional_user_from_request(
    request: Request,
    db: Session,
) -> UserORM | None:
    token = request.cookies.get(AUTH_COOKIE_NAME)

    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except ValueError:
        return None

    user_id = str(payload.get("sub") or "")

    if not user_id:
        return None

    return db.get(UserORM, user_id)

def _send_contact_email(
    topic: str,
    message: str,
    client_host: str | None = None,
    user: UserORM | None = None,
) -> None:
    if not settings.smtp_username or not settings.smtp_password:
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_USERNAME and SMTP_PASSWORD."
        )

    from_email = settings.smtp_from_email or settings.smtp_username

    email = EmailMessage()
    email["Subject"] = f"[HR Document Checker] {topic}"
    email["From"] = from_email
    email["To"] = settings.contact_email_to

    if user:
        user_info = [
            f"ID пользователя: {user.id}",
            f"Email пользователя: {user.email}",
            f"ФИО / имя: {user.full_name}",
            f"Роль: {user.role}",
        ]
    else:
        user_info = [
            "Пользователь: не авторизован",
        ]

    email.set_content(
        "\n".join(
            [
                "Новое обращение через форму HR Document Checker.",
                "",
                "Данные пользователя:",
                *user_info,
                "",
                f"Тема обращения: {topic}",
                "",
                "Описание:",
                message,
                "",
                "---",
                f"IP клиента: {client_host or 'не определён'}",
            ]
        )
    )

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        settings.smtp_host,
        settings.smtp_port,
        context=context,
        timeout=20,
    ) as server:
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(email)


def _send_password_reset_link_if_possible(
    request: Request,
    recipient_email: str,
    token: str,
) -> None:
    reset_url = build_password_reset_url(request, token)

    try:
        PasswordResetEmailService().send_reset_link(
            recipient_email=recipient_email,
            reset_url=reset_url,
        )
    except RuntimeError as error:
        logger.warning(
            "password_reset_email_not_configured email=%s error=%s reset_url=%s",
            recipient_email,
            error,
            reset_url,
        )
    except Exception:
        logger.exception("password_reset_email_send_failed email=%s", recipient_email)


@router.post("/contact")
async def submit_contact_form(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    form = await request.form()

    topic = str(form.get("topic") or "").strip()
    message = str(form.get("message") or "").strip()

    if not topic:
        return JSONResponse(
            {"success": False, "message": "Выберите тему обращения."},
            status_code=400,
        )

    if not message:
        return JSONResponse(
            {"success": False, "message": "Введите описание обращения."},
            status_code=400,
        )

    if len(message) > 5000:
        return JSONResponse(
            {
                "success": False,
                "message": "Описание слишком длинное. Сократите текст до 5000 символов.",
            },
            status_code=400,
        )
    
    user = _get_optional_user_from_request(request, db)

    try:
        await run_in_threadpool(
            _send_contact_email,
            topic,
            message,
            request.client.host if request.client else None,
            user,
        )
    except RuntimeError as error:
        logger.warning("contact_email_not_configured error=%s", error)

        return JSONResponse(
            {
                "success": False,
                "message": (
                    "Отправка почты пока не настроена на сервере. "
                    "Проверьте SMTP_USERNAME и SMTP_PASSWORD."
                ),
            },
            status_code=503,
        )
    except Exception:
        logger.exception("contact_email_send_failed")

        return JSONResponse(
            {
                "success": False,
                "message": "Не удалось отправить письмо. Попробуйте позже.",
            },
            status_code=500,
        )

    return JSONResponse(
        {
            "success": True,
            "message": "Письмо отправлено. Мы получили ваше обращение.",
        }
    )


def _template(
    request: Request,
    name: str,
    context: dict,
    status_code: int = 200,
):
    context["request"] = request

    return templates.TemplateResponse(
        request=request,
        name=name,
        context=context,
        status_code=status_code,
    )


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(
        url=url,
        status_code=303,
    )


def _validate_file_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix not in {".docx", ".pdf"}:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только файлы .docx и .pdf",
        )

    return suffix


MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024
AVATAR_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def _detect_avatar_content_type(content: bytes) -> str | None:
    format_content_types = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }

    try:
        with Image.open(BytesIO(content)) as image:
            if image.width > 4096 or image.height > 4096:
                return None

            image.verify()
            return format_content_types.get(image.format or "")
    except (OSError, SyntaxError, UnidentifiedImageError):
        return None


async def _save_upload_to_temp_file(file: UploadFile, suffix: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        content = await file.read()
        temporary_file.write(content)
        return Path(temporary_file.name)
    
def _validate_rag_source_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix not in RagSourceService.SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только RAG-источники .docx, .pdf, .txt и .md",
        )

    return suffix


async def _save_rag_source_upload_to_temp_file(
    file: UploadFile,
    suffix: str,
) -> tuple[Path, int]:
    content = await file.read()
    file_size_bytes = len(content)

    if file_size_bytes > RagSourceService.MAX_SINGLE_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Файл RAG-источника слишком большой. Максимальный размер — 15 МБ.",
        )

    with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        temporary_file.write(content)

        return Path(temporary_file.name), file_size_bytes


def _user_can_manage_rag_sources(user: UserORM) -> bool:
    return user.role in {"hr", "admin"}


def _bytes_to_mb(value: int) -> float:
    return round(value / 1024 / 1024, 2)


def _render_rag_sources_page(
    request: Request,
    db: Session,
    user: UserORM,
    error: str | None = None,
    success: str | None = None,
    status_code: int = 200,
):
    source_service = RagSourceService(db)
    rag_index_service = RagIndexService(db)

    sources = source_service.list_sources_for_user(
        user_id=user.id,
        user_role=user.role,
        include_inactive=True,
        limit=1000,
    )

    rag_status = rag_index_service.get_user_status(
        owner_user_id=user.id,
    )

    if user.role == "admin":
        active_storage_bytes = sum(
            source.file_size_bytes
            for source in sources
            if source.is_active
        )
    else:
        active_storage_bytes = source_service.get_active_storage_usage_bytes(user.id)

    return _template(
        request=request,
        name="rag_sources.html",
        context={
            "page_title": "RAG-источники",
            "user": user,
            "sources": sources,
            "rag_status": rag_status,
            "error": error,
            "success": success,
            "active_storage_bytes": active_storage_bytes,
            "active_storage_mb": _bytes_to_mb(active_storage_bytes),
            "max_file_size_mb": _bytes_to_mb(
                RagSourceService.MAX_SINGLE_FILE_SIZE_BYTES
            ),
            "max_storage_mb": _bytes_to_mb(
                RagSourceService.MAX_USER_STORAGE_BYTES
            ),
            "source_type_options": [
                ("vacancy", "Вакансия"),
                ("requirements", "Требования"),
                ("checklist", "Чек-лист"),
                ("policy", "Регламент"),
                ("other", "Другое"),
            ],
        },
        status_code=status_code,
    )


def _extract_token_from_request(request: Request) -> str | None:
    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)

    if cookie_token:
        return cookie_token

    authorization = request.headers.get("Authorization")

    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()

    return None


def _get_current_web_user(
    request: Request,
    db: Session,
) -> UserORM | None:
    token = _extract_token_from_request(request)

    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except ValueError:
        return None

    user_id = str(payload.get("sub", ""))
    user = UserService(db).get_by_id(user_id)

    if user is None or not user.is_active:
        return None

    return user


def _require_web_user(
    request: Request,
    db: Session,
) -> UserORM:
    user = _get_current_web_user(request, db)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    return user


def _dashboard_template_for_role(role: str) -> str:
    if role == "admin":
        return "admin_dashboard.html"

    if role == "hr":
        return "hr_dashboard.html"

    return "candidate_dashboard.html"


def _create_login_response(user: UserORM) -> RedirectResponse:
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    response = _redirect("/web/dashboard")
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )

    return response


@router.get("/")
def web_index(
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is not None:
        return _redirect("/web/dashboard")

    return _template(
        request=request,
        name="landing.html",
        context={
            "page_title": "HR Document Checker",
            "user": None,
        },
    )


@router.get("/login")
def show_login_page(
    request: Request,
    password_reset: str | None = None,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is not None:
        return _redirect("/web/dashboard")

    return _template(
        request=request,
        name="login.html",
        context={
            "page_title": "Вход",
            "error": None,
            "success": (
                "Пароль обновлён. Теперь войдите с новым паролем."
                if password_reset == "success"
                else None
            ),
        },
    )


@router.post("/login")
def login_web_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = UserService(db).authenticate(
        email=email,
        password=password,
    )

    if user is None:
        return _template(
            request=request,
            name="login.html",
            context={
                "page_title": "Вход",
                "error": "Неверный email или пароль.",
                "success": None,
            },
            status_code=401,
        )

    return _create_login_response(user)


@router.get("/password-reset/request")
def show_password_reset_request_page(
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is not None:
        return _redirect("/web/dashboard")

    return _template(
        request=request,
        name="password_reset_request.html",
        context={
            "page_title": "Восстановление пароля",
            "user": None,
            "error": None,
            "success": None,
            "email": "",
        },
    )


@router.post("/password-reset/request")
def request_password_reset_web(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        reset_request = PasswordResetRequest(email=email)
    except ValidationError:
        return _template(
            request=request,
            name="password_reset_request.html",
            context={
                "page_title": "Восстановление пароля",
                "user": None,
                "error": "Введите корректный email.",
                "success": None,
                "email": email,
            },
            status_code=400,
        )

    token = PasswordResetService(db).create_reset_token(str(reset_request.email))

    if token is not None:
        _send_password_reset_link_if_possible(
            request=request,
            recipient_email=str(reset_request.email),
            token=token,
        )

    return _template(
        request=request,
        name="password_reset_request.html",
        context={
            "page_title": "Восстановление пароля",
            "user": None,
            "error": None,
            "success": (
                "Если активный аккаунт с таким email существует, мы отправили "
                "ссылку для восстановления пароля."
            ),
            "email": "",
        },
    )


@router.get("/password-reset/confirm")
def show_password_reset_confirm_page(
    request: Request,
    token: str = "",
    db: Session = Depends(get_db),
):
    is_valid_token = bool(token) and PasswordResetService(db).is_token_valid(token)

    return _template(
        request=request,
        name="password_reset_confirm.html",
        context={
            "page_title": "Новый пароль",
            "user": None,
            "token": token,
            "is_valid_token": is_valid_token,
            "error": (
                None
                if is_valid_token
                else "Ссылка для восстановления пароля недействительна или истекла."
            ),
        },
        status_code=200 if is_valid_token else 400,
    )


@router.post("/password-reset/confirm")
def confirm_password_reset_web(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    if new_password != new_password_confirm:
        return _template(
            request=request,
            name="password_reset_confirm.html",
            context={
                "page_title": "Новый пароль",
                "user": None,
                "token": token,
                "is_valid_token": True,
                "error": "Пароли не совпадают.",
            },
            status_code=400,
        )

    try:
        reset_request = PasswordResetConfirmRequest(
            token=token,
            new_password=new_password,
        )
    except ValidationError:
        return _template(
            request=request,
            name="password_reset_confirm.html",
            context={
                "page_title": "Новый пароль",
                "user": None,
                "token": token,
                "is_valid_token": True,
                "error": "Пароль должен быть от 6 до 128 символов.",
            },
            status_code=400,
        )

    was_reset = PasswordResetService(db).reset_password(
        token=reset_request.token,
        new_password=reset_request.new_password,
    )

    if not was_reset:
        return _template(
            request=request,
            name="password_reset_confirm.html",
            context={
                "page_title": "Новый пароль",
                "user": None,
                "token": token,
                "is_valid_token": False,
                "error": "Ссылка для восстановления пароля недействительна или истекла.",
            },
            status_code=400,
        )

    response = _redirect("/web/login?password_reset=success")
    response.delete_cookie(AUTH_COOKIE_NAME)

    return response


@router.get("/register")
def show_register_page(
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is not None:
        return _redirect("/web/dashboard")

    return _template(
        request=request,
        name="register.html",
        context={
            "page_title": "Регистрация",
            "error": None,
        },
    )


@router.post("/register")
def register_web_user(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        create_request = UserCreateRequest(
            email=email,
            full_name=full_name,
            password=password,
            role=role,
        )

        user = UserService(db).create_user(create_request)

    except (ValueError, ValidationError) as error:
        return _template(
            request=request,
            name="register.html",
            context={
                "page_title": "Регистрация",
                "error": _localize_web_error(error),
            },
            status_code=400,
        )

    return _create_login_response(user)


@router.get("/logout")
def logout_web_user():
    response = _redirect("/web/login")
    response.delete_cookie(AUTH_COOKIE_NAME)

    return response


@router.get("/dashboard")
def show_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is None:
        return _redirect("/web/login")

    storage_service = ReportStorageService(db)
    reports = storage_service.list_report_records_for_user(
        user_id=user.id,
        user_role=user.role,
        limit=5,
    )

    return _template(
        request=request,
        name=_dashboard_template_for_role(user.role),
        context={
            "page_title": "Панель управления",
            "user": user,
            "reports": reports,
        },
    )


@router.get("/profile")
def show_profile(
    request: Request,
    avatar: str | None = None,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is None:
        return _redirect("/web/login")

    storage_service = ReportStorageService(db)
    reports = storage_service.list_report_records_for_user(
        user_id=user.id,
        user_role=user.role,
        limit=5,
    )

    return _template(
        request=request,
        name="profile.html",
        context={
            "page_title": "Личный кабинет",
            "user": user,
            "reports": reports,
            "success": (
                "Аватар успешно обновлён."
                if avatar == "updated"
                else None
            ),
            "error": None,
        },
    )


@router.get("/profile/avatar")
def get_profile_avatar(
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_web_user(request, db)

    if not user.avatar_data or not user.avatar_content_type:
        raise HTTPException(status_code=404, detail="Avatar not found.")

    return Response(
        content=user.avatar_data,
        media_type=user.avatar_content_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/profile/avatar")
async def upload_profile_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = _require_web_user(request, db)
    content = await avatar.read(MAX_AVATAR_SIZE_BYTES + 1)

    if not content:
        error = "Выберите изображение для загрузки."
    elif len(content) > MAX_AVATAR_SIZE_BYTES:
        error = "Размер аватара не должен превышать 2 МБ."
    else:
        detected_content_type = _detect_avatar_content_type(content)
        declared_content_type = (avatar.content_type or "").lower()

        if (
            detected_content_type is None
            or detected_content_type not in AVATAR_CONTENT_TYPES
            or (
                declared_content_type
                and declared_content_type not in AVATAR_CONTENT_TYPES
            )
        ):
            error = "Поддерживаются только изображения PNG, JPEG и WebP."
        else:
            user.avatar_data = content
            user.avatar_content_type = detected_content_type
            db.commit()
            return _redirect("/web/profile?avatar=updated")

    return _template(
        request=request,
        name="profile.html",
        context={
            "page_title": "Личный кабинет",
            "user": user,
            "reports": [],
            "success": None,
            "error": error,
        },
        status_code=400,
    )


@router.get("/reports")
def show_reports_history(
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is None:
        return _redirect("/web/login")

    storage_service = ReportStorageService(db)
    reports = storage_service.list_report_records_for_user(
        user_id=user.id,
        user_role=user.role,
        limit=100,
    )

    return _template(
        request=request,
        name="reports_history.html",
        context={
            "page_title": "История проверок",
            "user": user,
            "reports": reports,
        },
    )


@router.get("/reports/{report_id}")
def show_saved_report(
    report_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is None:
        return _redirect("/web/login")

    storage_service = ReportStorageService(db)

    if not storage_service.user_can_access_report(
        report_id=report_id,
        user_id=user.id,
        user_role=user.role,
    ):
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Доступ запрещён",
                "user": user,
                "status_code": 403,
                "error": "Недостаточно прав для просмотра этого отчёта.",
            },
            status_code=403,
        )

    report = storage_service.get_report(report_id)

    if report is None:
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Отчёт не найден",
                "user": user,
                "status_code": 404,
                "error": "Отчёт не найден.",
            },
            status_code=404,
        )

    report.technical_info.metadata["saved_to_db"] = True

    return _template(
        request=request,
        name="report.html",
        context={
            "page_title": "Сохранённый отчёт",
            "user": user,
            "report": report,
        },
    )

@router.get("/rag/sources")
def show_rag_sources_page(
    request: Request,
    error: str | None = None,
    success: str | None = None,
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is None:
        return _redirect("/web/login")

    if not _user_can_manage_rag_sources(user):
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Доступ запрещён",
                "user": user,
                "status_code": 403,
                "error": "RAG-источники доступны только HR-специалистам и администраторам.",
            },
            status_code=403,
        )

    return _render_rag_sources_page(
        request=request,
        db=db,
        user=user,
        error=error,
        success=success,
    )


@router.post("/rag/sources/upload")
async def upload_web_rag_source(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source_type: str = Form("other"),
    db: Session = Depends(get_db),
):
    user = _require_web_user(request, db)

    if not _user_can_manage_rag_sources(user):
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Доступ запрещён",
                "user": user,
                "status_code": 403,
                "error": "RAG-источники доступны только HR-специалистам и администраторам.",
            },
            status_code=403,
        )

    original_filename = file.filename or ""

    if not original_filename:
        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            error="Не указано имя файла.",
            status_code=400,
        )

    temporary_path: Path | None = None

    try:
        suffix = _validate_rag_source_suffix(original_filename)

        temporary_path, file_size_bytes = await _save_rag_source_upload_to_temp_file(
            file=file,
            suffix=suffix,
        )

        source_service = RagSourceService(db)
        source_service.create_source_from_file(
            file_path=temporary_path,
            original_filename=original_filename,
            owner_user_id=user.id,
            title=title,
            source_type=source_type,
            file_size_bytes=file_size_bytes,
        )

        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            success="RAG-источник успешно загружен.",
        )

    except HTTPException as error:
        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            error=str(error.detail),
            status_code=error.status_code,
        )

    except ValueError as error:
        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            error=str(error),
            status_code=400,
        )

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


@router.post("/rag/reindex")
def reindex_web_rag_sources(
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_web_user(request, db)

    if not _user_can_manage_rag_sources(user):
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Доступ запрещён",
                "user": user,
                "status_code": 403,
                "error": "RAG-источники доступны только HR-специалистам и администраторам.",
            },
            status_code=403,
        )

    try:
        rag_index = RagIndexService(db).reindex_user_sources(
            owner_user_id=user.id,
        )

    except Exception as error:
        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            error=f"Ошибка переиндексации RAG: {error}",
            status_code=500,
        )

    return _render_rag_sources_page(
        request=request,
        db=db,
        user=user,
        success=(
            "RAG-индекс переиндексирован. "
            f"Активных источников: {rag_index.sources_count}, "
            f"чанков: {rag_index.chunks_count}."
        ),
    )

@router.post("/rag/sources/{source_id}/delete")
def delete_web_rag_source(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_web_user(request, db)

    if not _user_can_manage_rag_sources(user):
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Доступ запрещён",
                "user": user,
                "status_code": 403,
                "error": "RAG-источники доступны только HR-специалистам и администраторам.",
            },
            status_code=403,
        )

    source_service = RagSourceService(db)
    deleted = source_service.deactivate_source_for_user(
        source_id=source_id,
        user_id=user.id,
        user_role=user.role,
    )

    if not deleted:
        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            error="RAG-источник не найден или недоступен.",
            status_code=404,
        )

    return _render_rag_sources_page(
        request=request,
        db=db,
        user=user,
        success="RAG-источник отключён.",
    )

@router.post("/rag/sources/{source_id}/activate")
def activate_web_rag_source(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_web_user(request, db)

    if not _user_can_manage_rag_sources(user):
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Доступ запрещён",
                "user": user,
                "status_code": 403,
                "error": "RAG-источники доступны только HR-специалистам и администраторам.",
            },
            status_code=403,
        )

    source_service = RagSourceService(db)

    try:
        activated = source_service.activate_source_for_user(
            source_id=source_id,
            user_id=user.id,
            user_role=user.role,
        )

    except ValueError as error:
        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            error=str(error),
            status_code=400,
        )

    if not activated:
        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            error="RAG-источник не найден или недоступен.",
            status_code=404,
        )

    return _render_rag_sources_page(
        request=request,
        db=db,
        user=user,
        success="RAG-источник включён.",
    )

@router.post("/rag/sources/{source_id}/permanent-delete")
def permanently_delete_web_rag_source(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_web_user(request, db)

    if not _user_can_manage_rag_sources(user):
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Доступ запрещён",
                "user": user,
                "status_code": 403,
                "error": "RAG-источники доступны только HR-специалистам и администраторам.",
            },
            status_code=403,
        )

    source_service = RagSourceService(db)
    deleted = source_service.permanently_delete_source_for_user(
        source_id=source_id,
        user_id=user.id,
        user_role=user.role,
    )

    if not deleted:
        return _render_rag_sources_page(
            request=request,
            db=db,
            user=user,
            error="RAG-источник не найден или недоступен.",
            status_code=404,
        )

    return _render_rag_sources_page(
        request=request,
        db=db,
        user=user,
        success="RAG-источник полностью удалён.",
    )

@router.post("/report")
async def build_report_page(
    request: Request,
    file: UploadFile = File(...),
    vacancy_text: str | None = Form(None),
    storage_mode: StorageMode = Form(StorageMode.TEMPORARY),
    db: Session = Depends(get_db),
):
    current_user = _require_web_user(request, db)

    filename = file.filename or ""
    suffix = _validate_file_suffix(filename)

    temporary_path: Path | None = None
    started_at = perf_counter()

    try:
        temporary_path = await _save_upload_to_temp_file(file, suffix)

        service = DocumentProcessingService()
        parsed_document = service.parse_and_enrich(
            file_path=temporary_path,
            original_filename=filename,
            storage_mode=storage_mode,
        )

        formal_check_response = FormalCheckCoordinator().run(parsed_document)

        semantic_check_response = SemanticCheckCoordinator().run(
            document=parsed_document,
            vacancy_text=vacancy_text,
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
        )

        report = ReportBuilder().build(
            document=parsed_document,
            formal_check_response=formal_check_response,
            semantic_check_response=semantic_check_response,
            vacancy_text=vacancy_text,
        )

        if storage_mode == StorageMode.NO_STORE:
            report.technical_info.metadata["saved_to_db"] = False
        else:
            report.technical_info.metadata["saved_to_db"] = True

            ReportStorageService(db).save_report(
                document=parsed_document,
                report=report,
                owner_user_id=current_user.id,
            )

        duration_ms = round((perf_counter() - started_at) * 1000, 3)

        metrics.record_document_processed(
            duration_ms=duration_ms,
            issues_count=report.total_issues,
        )
        metrics.record_report_generated()

        logger.info(
            "web_report_generated document_id=%s report_id=%s owner_user_id=%s issues=%s storage_mode=%s saved_to_db=%s duration_ms=%s",
            report.document_id,
            report.report_id,
            current_user.id,
            report.total_issues,
            storage_mode.value,
            report.technical_info.metadata.get("saved_to_db"),
            duration_ms,
        )

        return _template(
            request=request,
            name="report.html",
            context={
                "page_title": "Результат проверки",
                "user": current_user,
                "report": report,
            },
        )

    except HTTPException as error:
        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Ошибка",
                "user": current_user,
                "status_code": error.status_code,
                "error": error.detail,
            },
            status_code=error.status_code,
        )

    except Exception as error:
        metrics.record_error()

        logger.exception(
            "web_report_generation_failed filename_suffix=%s storage_mode=%s owner_user_id=%s",
            suffix,
            storage_mode.value,
            current_user.id,
        )

        return _template(
            request=request,
            name="error.html",
            context={
                "page_title": "Ошибка",
                "user": current_user,
                "status_code": 400,
                "error": f"Ошибка при формировании отчёта: {error}",
            },
            status_code=400,
        )

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
