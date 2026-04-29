from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTH_COOKIE_NAME
from app.auth.security import create_access_token, decode_access_token
from app.coordinator.formal_check_coordinator import FormalCheckCoordinator
from app.coordinator.semantic_check_coordinator import SemanticCheckCoordinator
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.db.models import UserORM
from app.db.session import get_db
from app.reports.report_builder import ReportBuilder
from app.schemas.auth import UserCreateRequest
from app.schemas.common import StorageMode
from app.services.document_processing_service import DocumentProcessingService
from app.services.report_storage_service import ReportStorageService
from app.services.user_service import UserService


logger = get_logger(__name__)

router = APIRouter(prefix="/web", tags=["web"])
templates = Jinja2Templates(directory="app/web/templates")


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


async def _save_upload_to_temp_file(file: UploadFile, suffix: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        content = await file.read()
        temporary_file.write(content)
        return Path(temporary_file.name)


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

    if user is None:
        return _redirect("/web/login")

    return _redirect("/web/dashboard")


@router.get("/login")
def show_login_page(
    request: Request,
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
            },
            status_code=401,
        )

    return _create_login_response(user)


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
                "error": str(error),
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
        limit=20,
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
    db: Session = Depends(get_db),
):
    user = _get_current_web_user(request, db)

    if user is None:
        return _redirect("/web/login")

    storage_service = ReportStorageService(db)
    reports = storage_service.list_report_records_for_user(
        user_id=user.id,
        user_role=user.role,
        limit=20,
    )

    return _template(
        request=request,
        name="profile.html",
        context={
            "page_title": "Личный кабинет",
            "user": user,
            "reports": reports,
        },
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