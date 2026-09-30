import smtplib
import ssl

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Diagnose email delivery. Reports the active backend, opens a real SMTP '
        'connection to prove reachability, then attempts to send a test message. '
        'Use this before blaming the login flow — it isolates config problems from '
        'credential problems.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--to', default=None,
            help='Recipient address (default: DEFAULT_FROM_EMAIL).',
        )
        parser.add_argument(
            '--skip-send', action='store_true',
            help='Only report config and TCP/TLS reachability; do not authenticate or send.',
        )

    def handle(self, *args, **options):
        host = settings.EMAIL_HOST
        port = settings.EMAIL_PORT
        user = settings.EMAIL_HOST_USER
        backend = settings.EMAIL_BACKEND
        to = options['to'] or settings.DEFAULT_FROM_EMAIL

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Email configuration'))
        self.stdout.write(f'  EMAIL_BACKEND   = {backend}')
        self.stdout.write(f'  EMAIL_HOST      = {host}')
        self.stdout.write(f'  EMAIL_PORT      = {port}')
        self.stdout.write(f'  EMAIL_USE_TLS   = {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'  EMAIL_USE_SSL   = {settings.EMAIL_USE_SSL}')
        self.stdout.write(f'  EMAIL_TIMEOUT   = {settings.EMAIL_TIMEOUT}')
        self.stdout.write(f'  FROM            = {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'  USER            = {user or "(unset)"}')
        self.stdout.write(f'  PASSWORD        = {"(set)" if settings.EMAIL_HOST_PASSWORD else "(unset)"}')

        if backend.endswith('console.EmailBackend'):
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'Console backend is active — emails are printed to the terminal running '
                'runserver instead of being sent. Login OTPs are working, but the code '
                'lands in the console, not an inbox.'
            ))
            self.stdout.write(self.style.WARNING(
                'To enable real delivery, set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in '
                'backend/.env (both must be non-empty; settings.py auto-selects SMTP).'
            ))
            return

        if not user or not settings.EMAIL_HOST_PASSWORD:
            self.stdout.write(self.style.ERROR(
                '  SMTP backend selected but EMAIL_HOST_USER / EMAIL_HOST_PASSWORD is '
                'missing. Set both in backend/.env.'
            ))
            return

        # Reachability: proves DNS, TCP and the TLS handshake all work. Doing this
        # before authenticating separates "cannot reach the server" from "the server
        # rejected our credentials" — the two have very different fixes.
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('SMTP reachability'))
        try:
            with smtplib.SMTP(host, port, timeout=settings.EMAIL_TIMEOUT) as smtp:
                smtp.ehlo()
                if settings.EMAIL_USE_SSL:
                    smtp.starttls(context=ssl.create_default_context())
                elif settings.EMAIL_USE_TLS:
                    smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            self.stdout.write(self.style.SUCCESS(
                f'  Connected to {host}:{port} and completed the TLS handshake.'
            ))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  Could not reach {host}:{port} — {exc}'))
            self.stdout.write(self.style.ERROR(
                '  Check EMAIL_HOST / EMAIL_PORT. For Gmail use smtp.gmail.com on 587 '
                '(STARTTLS) or 465 (implicit SSL, with EMAIL_USE_TLS=False).'
            ))
            return

        if options['skip_send']:
            self.stdout.write(self.style.SUCCESS('  --skip-send given, stopping before auth.'))
            return

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Authentication + send'))
        try:
            sent = send_mail(
                'Bhavesh RTO CRM — test email',
                'If you are reading this, SMTP delivery is working and login OTPs '
                'will arrive in the inbox.',
                settings.DEFAULT_FROM_EMAIL,
                [to],
                fail_silently=False,
            )
        except smtplib.SMTPAuthenticationError:
            self.stdout.write(self.style.ERROR(
                '  535 Username and Password not accepted.'
            ))
            self.stdout.write(self.style.ERROR(
                '  The server was reached and the connection is healthy — only the '
                'credential was refused, so host/port/TLS settings are correct.'
            ))
            self.stdout.write(self.style.ERROR(
                '  For Gmail the password must be a 16-character App Password, not the '
                'account password: Google Account -> Security -> 2-Step Verification '
                '(must be ON) -> App passwords -> Generate. App passwords are bound to '
                'the account that was signed in when they were created, and enabling '
                '2FA can revoke existing ones. They can also take ~15 minutes to activate.'
            ))
        except smtplib.SMTPException as exc:
            self.stdout.write(self.style.ERROR(f'  SMTP error: {exc}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  {type(exc).__name__}: {exc}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  Sent 1 message to {to}.'))
            self.stdout.write(self.style.SUCCESS('  Login OTPs will now be emailed.'))
