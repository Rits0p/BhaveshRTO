import json
from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from reminders.services import (
    OpenWAProvider,
    MetaCloudAPIProvider,
    StubWhatsAppProvider,
    get_whatsapp_provider,
)


class OpenWAProviderTestCase(TestCase):
    def setUp(self):
        self.provider = OpenWAProvider(
            server_url="http://localhost:2785",
            session_id="test-session",
            api_key="secret-api-key",
        )

    def test_clean_phone_formatting(self):
        """Test phone number cleaning and formatting for OpenWA."""
        self.assertEqual(self.provider._clean_phone("9876543210"), "919876543210@c.us")
        self.assertEqual(self.provider._clean_phone("+91 98765-43210"), "919876543210@c.us")
        self.assertEqual(self.provider._clean_phone("919876543210@c.us"), "919876543210@c.us")

    @patch("requests.post")
    def test_send_message_success(self, mock_post):
        """Test sending a text message via OpenWA REST API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "id": "msg-123"}
        mock_post.return_value = mock_response

        res = self.provider.send_message("9876543210", "Hello World")

        self.assertEqual(res, {"status": "success", "id": "msg-123"})
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://localhost:2785/api/sessions/test-session/messages/send-text")
        self.assertEqual(kwargs["json"], {"chatId": "919876543210@c.us", "text": "Hello World"})
        self.assertEqual(kwargs["headers"]["X-API-Key"], "secret-api-key")

    @patch("requests.post")
    def test_send_document_pdf_success(self, mock_post):
        """Test sending a PDF document via OpenWA REST API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "id": "doc-456"}
        mock_post.return_value = mock_response

        dummy_pdf_bytes = b"%PDF-1.4 dummy content"
        media_id = self.provider.upload_media(dummy_pdf_bytes, "receipt.pdf", "application/pdf")
        self.assertTrue(media_id.startswith("data:application/pdf;base64,"))

        res = self.provider.send_document(
            to_number="9876543210",
            media_id=media_id,
            caption="Your receipt",
            filename="receipt.pdf",
        )

        self.assertEqual(res, {"status": "success", "id": "doc-456"})
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://localhost:2785/api/sessions/test-session/messages/send-document")
        self.assertEqual(kwargs["json"]["chatId"], "919876543210@c.us")
        self.assertEqual(kwargs["json"]["filename"], "receipt.pdf")
        self.assertEqual(kwargs["json"]["caption"], "Your receipt")
        self.assertEqual(kwargs["json"]["mimetype"], "application/pdf")
        self.assertTrue(kwargs["json"]["base64"].startswith("data:application/pdf;base64,"))


class GetWhatsAppProviderTestCase(TestCase):
    @override_settings(WHATSAPP_PROVIDER="openwa", OPENWA_SERVER_URL="http://localhost:2785")
    def test_explicit_openwa_provider(self):
        provider = get_whatsapp_provider()
        self.assertIsInstance(provider, OpenWAProvider)

    @override_settings(WHATSAPP_PROVIDER="meta", WHATSAPP_API_TOKEN="token", WHATSAPP_PHONE_NUMBER_ID="123")
    def test_explicit_meta_provider(self):
        provider = get_whatsapp_provider()
        self.assertIsInstance(provider, MetaCloudAPIProvider)

    @override_settings(WHATSAPP_PROVIDER="stub")
    def test_explicit_stub_provider(self):
        provider = get_whatsapp_provider()
        self.assertIsInstance(provider, StubWhatsAppProvider)
