import smtplib
import ssl

from email.message import EmailMessage

from app.core.config import settings


class PasswordResetEmailService:
    def send_reset_link(
        self,
        recipient_email: str,
        reset_url: str,
    ) -> None:
        if not settings.smtp_username or not settings.smtp_password:
            raise RuntimeError(
                "SMTP is not configured. Set SMTP_USERNAME and SMTP_PASSWORD."
            )

        from_email = settings.smtp_from_email or settings.smtp_username

        email = EmailMessage()
        email["Subject"] = "[HR Document Checker] Восстановление пароля"
        email["From"] = from_email
        email["To"] = recipient_email
        email.set_content(
            "\n".join(
                [
                    "Здравствуйте!",
                    "",
                    "Мы получили запрос на восстановление пароля в HR Document Checker.",
                    "Чтобы задать новый пароль, перейдите по ссылке:",
                    reset_url,
                    "",
                    (
                        "Ссылка действует "
                        f"{settings.password_reset_token_ttl_minutes} минут."
                    ),
                    "Если вы не запрашивали восстановление пароля, просто игнорируйте это письмо.",
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
