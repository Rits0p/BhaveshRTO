import io
import json
from abc import ABC, abstractmethod

from django.conf import settings

from .models import MessageLog

# Branded header prepended to every outgoing message.
MSG_HEADER = (
    "🏢 *BHAVESH SOLANKI*\n"
    "   *RTO & Insurance Advisor*\n"
    "   📍 Trusted. Reliable. Fast.\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
)

# Professional, category-specific WhatsApp reminder templates.
# Placeholders: {name} = customer name, {end_date} = formatted expiry date.
# NOTE: MSG_HEADER is prepended by build_message() — do not repeat it here.
CATEGORY_TEMPLATES = {
    'insurance': (
        "🚗 *Vehicle Insurance Renewal Reminder*\n\n"
        "Dear *{name}*,\n\n"
        "We would like to inform you that your *Vehicle Insurance Policy* is due to expire on *{end_date}*.\n\n"
        "⚠️ Driving without valid insurance is illegal and puts you at financial risk. "
        "Please renew it before the due date to stay protected and legally compliant.\n\n"
        "📞 Contact us today to renew your policy quickly and hassle-free.\n\n"
        "_Thank you for trusting us with your needs._ 🙏"
    ),
    'permit': (
        "📋 *Vehicle Permit Renewal Reminder*\n\n"
        "Dear *{name}*,\n\n"
        "Your *Vehicle Permit* is expiring on *{end_date}*.\n\n"
        "⚠️ Operating a commercial vehicle without a valid permit can result in heavy fines "
        "and legal penalties. Please ensure timely renewal to avoid any disruption to your business.\n\n"
        "📞 Reach out to us and we will handle the renewal process for you smoothly.\n\n"
        "_Thank you for trusting us with your needs._ 🙏"
    ),
    'fitness': (
        "🔧 *Vehicle Fitness Certificate Renewal Reminder*\n\n"
        "Dear *{name}*,\n\n"
        "Your *Vehicle Fitness Certificate* is due to expire on *{end_date}*.\n\n"
        "⚠️ A valid fitness certificate is mandatory for your vehicle to operate legally on the road. "
        "Please renew it on time to avoid fines and vehicle detention.\n\n"
        "📞 Contact us to schedule your fitness renewal without any stress.\n\n"
        "_Thank you for trusting us with your needs._ 🙏"
    ),
    'puc': (
        "🌿 *PUC Certificate Renewal Reminder*\n\n"
        "Dear *{name}*,\n\n"
        "Your *Pollution Under Control (PUC) Certificate* is expiring on *{end_date}*.\n\n"
        "⚠️ A valid PUC certificate is legally required for every vehicle. "
        "Driving without it can attract on-the-spot fines. Please renew it promptly.\n\n"
        "📞 We can assist you with a quick and easy PUC renewal. Get in touch today!\n\n"
        "_Thank you for trusting us with your needs._ 🙏"
    ),
    'fitness_puc': (
        "🔧 *Fitness & PUC Certificate Renewal Reminder*\n\n"
        "Dear *{name}*,\n\n"
        "Your *Vehicle Fitness & PUC Certificate* is due to expire on *{end_date}*.\n\n"
        "⚠️ Both fitness and PUC certifications are mandatory for your vehicle to remain road-legal. "
        "Timely renewal ensures you avoid fines and legal complications.\n\n"
        "📞 Contact us today — we will handle both renewals together for your convenience.\n\n"
        "_Thank you for trusting us with your needs._ 🙏"
    ),
    'tax': (
        "💰 *Road Tax Renewal Reminder*\n\n"
        "Dear *{name}*,\n\n"
        "Your *Road Tax* is due for renewal by *{end_date}*.\n\n"
        "⚠️ Non-payment of road tax can lead to penalties and your vehicle registration may be suspended. "
        "Please ensure timely payment to keep your vehicle documents valid.\n\n"
        "📞 We are here to assist you with the tax renewal process. Contact us now!\n\n"
        "_Thank you for trusting us with your needs._ 🙏"
    ),
    'license': (
        "🪪 *Driving License Renewal Reminder*\n\n"
        "Dear *{name}*,\n\n"
        "Your *Driving License* is expiring on *{end_date}*.\n\n"
        "⚠️ Driving with an expired license is a traffic offence and may lead to fines or legal action. "
        "Please renew your license well before the expiry date.\n\n"
        "📞 Contact us and we will guide you through the renewal process quickly and easily.\n\n"
        "_Thank you for trusting us with your needs._ 🙏"
    ),
}


def build_message(customer):
    template = CATEGORY_TEMPLATES.get(customer.category, CATEGORY_TEMPLATES['insurance'])
    end_date_str = customer.end_date.strftime('%d %b %Y') if customer.end_date else 'N/A'
    body = template.format(name=customer.name, end_date=end_date_str)
    # Prepend the company header so every message starts with the brand identity.
    return MSG_HEADER + body


class WhatsAppProvider(ABC):
    @abstractmethod
    def send_message(self, to_number: str, message: str) -> dict:
        """Send a text message; return a JSON-serializable provider response.
        Must raise on failure so the caller can log status=failed.
        """

    @abstractmethod
    def upload_media(self, file_bytes: bytes, filename: str, mime_type: str) -> str:
        """Upload a file and return a media_id usable in send_document."""

    @abstractmethod
    def send_document(self, to_number: str, media_id: str, caption: str, filename: str) -> dict:
        """Send a document message; return a JSON-serializable provider response."""


class StubWhatsAppProvider(WhatsAppProvider):
    """Default provider — logs to the console instead of calling a real API,
    so the whole reminder flow (and its tests) works without WhatsApp
    credentials configured.
    """

    def send_message(self, to_number, message):
        print(f"\n\U0001f4f1  [WhatsApp STUB] To {to_number}:\n{message}\n")
        return {'provider': 'stub', 'detail': 'Stub mode \u2014 logged to console, no real message sent.'}

    def upload_media(self, file_bytes, filename, mime_type):
        print(f"\n\U0001f4f1  [WhatsApp STUB] Uploaded media: {filename} ({mime_type}, {len(file_bytes)} bytes)")
        return 'stub-media-id-000'

    def send_document(self, to_number, media_id, caption, filename):
        print(f"\n\U0001f4f1  [WhatsApp STUB] To {to_number}: document '{filename}' caption='{caption}'")
        return {'provider': 'stub', 'detail': 'Stub mode \u2014 document logged to console, no real message sent.'}


class MetaCloudAPIProvider(WhatsAppProvider):
    """WhatsApp Cloud API (Meta) integration. Callers depend only on the
    WhatsAppProvider interface, never on this class directly, so a Twilio
    (or other) implementation could be swapped in later without touching
    `send_reminder()` below.
    """

    def __init__(self, token, phone_number_id):
        self.token = token
        self.phone_number_id = phone_number_id

    def _clean_phone(self, phone):
        """Strip spaces, dashes, and leading '+' for the WhatsApp API."""
        return phone.replace(' ', '').replace('-', '').lstrip('+')

    def send_message(self, to_number, message):
        import requests

        url = f'https://graph.facebook.com/v19.0/{self.phone_number_id}/messages'
        payload = {
            'messaging_product': 'whatsapp',
            'to': self._clean_phone(to_number),
            'type': 'text',
            'text': {'body': message},
        }
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def upload_media(self, file_bytes, filename, mime_type):
        import requests

        url = f'https://graph.facebook.com/v19.0/{self.phone_number_id}/media'
        headers = {'Authorization': f'Bearer {self.token}'}
        files = {
            'file': (filename, io.BytesIO(file_bytes), mime_type),
        }
        data = {
            'messaging_product': 'whatsapp',
            'type': mime_type,
        }
        response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        response.raise_for_status()
        return response.json()['id']

    def send_document(self, to_number, media_id, caption, filename):
        import requests

        url = f'https://graph.facebook.com/v19.0/{self.phone_number_id}/messages'
        payload = {
            'messaging_product': 'whatsapp',
            'to': self._clean_phone(to_number),
            'type': 'document',
            'document': {
                'id': media_id,
                'caption': caption,
                'filename': filename,
            },
        }
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()


import base64


class OpenWAProvider(WhatsAppProvider):
    """WhatsApp integration via OpenWA REST API (https://github.com/rmyndharis/OpenWA).
    Supports sending text messages and document/PDF files via self-hosted OpenWA REST gateway.
    """

    def __init__(self, server_url, session_id='default', api_key=''):
        self.server_url = server_url.rstrip('/')
        self.session_id = session_id
        self.api_key = api_key

    def _clean_phone(self, phone):
        """Clean phone number into international format / OpenWA chatId.
        Example: "+91 98765-43210" -> "919876543210@c.us"
        """
        digits = ''.join(c for c in str(phone) if c.isdigit())
        if len(digits) == 10:
            digits = '91' + digits
        if not digits.endswith('@c.us'):
            return f"{digits}@c.us"
        return digits

    def _get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def send_message(self, to_number, message):
        import requests

        chat_id = self._clean_phone(to_number)
        url = f'{self.server_url}/api/sessions/{self.session_id}/messages/send-text'
        payload = {
            'chatId': chat_id,
            'text': message,
        }

        headers = self._get_headers()
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 404:
            fallback_url = f'{self.server_url}/api/send-message'
            response = requests.post(fallback_url, json=payload, headers=headers, timeout=15)

        response.raise_for_status()
        return response.json()

    def upload_media(self, file_bytes, filename, mime_type):
        """Encodes file bytes into a base64 Data URL string to pass to send_document."""
        b64_data = base64.b64encode(file_bytes).decode('utf-8')
        return f"data:{mime_type};base64,{b64_data}"

    def send_document(self, to_number, media_id, caption, filename):
        import requests

        chat_id = self._clean_phone(to_number)
        url = f'{self.server_url}/api/sessions/{self.session_id}/messages/send-document'

        file_data = media_id if media_id.startswith('data:') else f"data:application/pdf;base64,{media_id}"

        payload = {
            'chatId': chat_id,
            'file': file_data,
            'filename': filename,
            'caption': caption,
        }

        headers = self._get_headers()
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 404:
            fallback_url = f'{self.server_url}/api/sessions/{self.session_id}/messages/send-file'
            response = requests.post(fallback_url, json=payload, headers=headers, timeout=30)

        response.raise_for_status()
        return response.json()


def get_whatsapp_provider():
    provider_type = getattr(settings, 'WHATSAPP_PROVIDER', 'auto').lower()

    if provider_type == 'openwa':
        return OpenWAProvider(
            server_url=settings.OPENWA_SERVER_URL,
            session_id=getattr(settings, 'OPENWA_SESSION_ID', 'default'),
            api_key=getattr(settings, 'OPENWA_API_KEY', ''),
        )
    elif provider_type == 'meta':
        return MetaCloudAPIProvider(settings.WHATSAPP_API_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID)
    elif provider_type == 'stub':
        return StubWhatsAppProvider()

    # Auto-detection mode:
    if settings.WHATSAPP_API_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
        return MetaCloudAPIProvider(settings.WHATSAPP_API_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID)
    if settings.OPENWA_SERVER_URL and (settings.OPENWA_SERVER_URL != 'http://localhost:2785' or getattr(settings, 'OPENWA_API_KEY', '')):
        return OpenWAProvider(
            server_url=settings.OPENWA_SERVER_URL,
            session_id=getattr(settings, 'OPENWA_SESSION_ID', 'default'),
            api_key=getattr(settings, 'OPENWA_API_KEY', ''),
        )
    return StubWhatsAppProvider()



def send_reminder(customer):
    """Builds the category-specific message, sends it via the configured
    WhatsApp provider, and ALWAYS logs the attempt to MessageLog — on
    success and on failure.

    Returns (message_log, success: bool).
    """
    provider = get_whatsapp_provider()
    message = build_message(customer)

    try:
        response = provider.send_message(customer.contact_number, message)
        log = MessageLog.objects.create(
            customer=customer,
            category=customer.category,
            message_body=message,
            status=MessageLog.Status.SENT,
            provider_response=json.dumps(response),
        )
        return log, True
    except Exception as exc:
        log = MessageLog.objects.create(
            customer=customer,
            category=customer.category,
            message_body=message,
            status=MessageLog.Status.FAILED,
            provider_response=str(exc),
        )
        return log, False


def send_receipt_via_whatsapp(receipt_type, receipt_id):
    """Generate a PDF receipt, upload it to WhatsApp as a media asset, and
    send it as a document message to the receipt's contact_number.

    receipt_type: 'customer' or 'manual'
    receipt_id: UUID of the Customer or ManualReceipt

    Returns (success: bool, message: str).
    """
    from customers.models import Customer
    from payments.models import ManualReceipt
    from payments.services import generate_manual_pdf_receipt, generate_pdf_receipt

    provider = get_whatsapp_provider()

    if isinstance(provider, StubWhatsAppProvider):
        return False, (
            'WhatsApp is not configured. '
            'Configure OpenWA (OPENWA_SERVER_URL) or Meta Cloud API (WHATSAPP_API_TOKEN) '
            'in backend/.env then restart the server.'
        )


    if receipt_type == 'customer':
        try:
            customer = Customer.objects.get(pk=receipt_id)
        except Customer.DoesNotExist:
            return False, 'Customer not found.'

        phone = customer.contact_number
        if not phone:
            return False, 'No contact number on file for this customer.'

        payments = list(customer.payments.all().order_by('-payment_date'))
        total_paid = sum(float(p.amount) for p in payments)
        total_pending = float(customer.amount_total or 0) - total_paid
        admin_name = 'Bhavesh Solanki'
        pdf_bytes = generate_pdf_receipt(customer, payments, total_paid, total_pending, admin_name=admin_name)
        filename = f"receipt_{customer.name.replace(' ', '_')}.pdf"
        caption = f"Payment receipt for {customer.name} — Bhavesh Solanki RTO & Insurance Advisor"

    elif receipt_type == 'manual':
        try:
            manual = ManualReceipt.objects.get(pk=receipt_id)
        except ManualReceipt.DoesNotExist:
            return False, 'Manual receipt not found.'

        phone = manual.contact_number
        if not phone:
            return False, 'No contact number on file for this receipt.'

        form_data = {
            'name': manual.name,
            'contact_number': manual.contact_number,
            'vehicle_number': manual.vehicle_number,
            'service': manual.service,
            'date': manual.date.strftime('%Y-%m-%d'),
            'amount_total': float(manual.amount_total),
            'amount_paid': float(manual.amount_paid),
            'amount_pending': float(manual.amount_pending),
            'method': manual.method,
            'receipt_number': manual.receipt_number,
        }
        admin_name = 'Bhavesh Solanki'
        pdf_bytes = generate_manual_pdf_receipt(form_data, admin_name=admin_name)
        filename = f"manual_receipt_{manual.name.replace(' ', '_')}.pdf"
        caption = f"Manual receipt {manual.receipt_number} — Bhavesh Solanki RTO & Insurance Advisor"
    else:
        return False, 'Invalid receipt type.'

    try:
        media_id = provider.upload_media(pdf_bytes, filename, 'application/pdf')
        response = provider.send_document(phone, media_id, caption, filename)
        return True, f'Receipt sent to {phone} successfully.'
    except Exception as exc:
        return False, f'Failed to send receipt via WhatsApp: {exc}'
