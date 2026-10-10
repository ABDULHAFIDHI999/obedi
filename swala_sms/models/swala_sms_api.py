# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
"""SwalaSMS gateway connector.

Any other module sends an SMS through SwalaSMS with a single call::

    result = self.env['swala.sms'].send(phone, message)
    # -> {'success': bool, 'response': str or False, 'error': str or False}

Credentials and the enable/disable switch are configured once in Settings, independently of
whichever module is actually sending messages - so when a message is sent anyhow it goes
through SwalaSMS once it's configured and enabled, with zero changes needed in the caller.

When SwalaSMS is disabled or has no API URL configured, a mock/test provider is used
automatically instead, so callers always get a well-formed result and keep working offline.

The real SwalaSMS API (https://swalasms.com/sms/developer/docs):

* Base URL: ``https://swalasms.com/api/v1``
* Auth: Bearer token - ``Authorization: Bearer <api_key>`` header
  (live keys look like ``swl_live_...``, sandbox keys ``swl_test_...``).
* Send one SMS: ``POST {base_url}/sms/messages`` with JSON body
  ``{"recipient": "+255712345678", "sender_id": "...", "body": "..."}``.
  Returns HTTP 202 with ``{"success": true, "data": {"status": "queued", ...}}`` once accepted
  for delivery (actual delivery is confirmed later via webhook/polling, not synchronously).
* Check balance (used for Test Connection): ``GET {base_url}/balance``.
  Response: ``{"success": true, "data": {"balance": "...", "currency": "SMS", ...}}``.
"""
import logging
import uuid
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover - requests should always be available in Odoo's venv
    requests = None

from odoo import models


class _SmsProviderBase:
    """Internal interface every concrete provider implements."""

    def __init__(self, config):
        self.config = config or {}

    def send(self, phone, message):
        """:return: dict with keys ``success`` (bool), ``response`` (str) and ``error`` (str or False)"""
        raise NotImplementedError

    def test_connection(self):
        raise NotImplementedError


class _TestSmsProvider(_SmsProviderBase):
    """Mock provider: never calls out to the network, always 'succeeds'. Used automatically
    whenever SwalaSMS is disabled or not configured, so callers keep working offline."""

    def send(self, phone, message):
        _logger.info("[SWALA SMS TEST PROVIDER] To: %s | Message: %s", phone, message)
        return {
            'success': True,
            'response': "MOCK: message accepted by test provider at %s" % datetime.now(),
            'error': False,
        }

    def test_connection(self):
        return {'success': True, 'response': "Test provider is always reachable.", 'error': False}


class _SwalaSmsProvider(_SmsProviderBase):
    """HTTP adapter for the real SwalaSMS gateway (``https://swalasms.com``), matching their
    official REST API exactly: Bearer token + ``POST {base_url}/sms/messages``."""

    def _base_url(self):
        return (self.config.get('api_url') or '').strip().rstrip('/')

    def _headers(self, idempotency_key=None):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': "Bearer %s" % (self.config.get('api_key') or ''),
        }
        if idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        return headers

    @staticmethod
    def _clean_phone(phone):
        """SwalaSMS requires E.164 format (e.g. +255712345678): keep the leading '+' and
        digits only, strip spaces/dashes."""
        phone = phone or ''
        plus = '+' if phone.strip().startswith('+') else ''
        digits = ''.join(ch for ch in phone if ch.isdigit())
        return plus + digits

    def send(self, phone, message):
        if requests is None:
            return {'success': False, 'response': False, 'error': "The 'requests' library is not available."}
        base_url = self._base_url()
        if not base_url:
            return {'success': False, 'response': False, 'error': "SwalaSMS API URL is not configured."}
        payload = {
            'recipient': self._clean_phone(phone),
            'sender_id': self.config.get('sender_id'),
            'body': message,
        }
        try:
            response = requests.post(
                "%s/sms/messages" % base_url, json=payload,
                headers=self._headers(idempotency_key=str(uuid.uuid4())), timeout=15)
            try:
                data = response.json()
            except ValueError:
                data = {}
            sms_data = data.get('data') or {}
            ok = response.status_code == 202 and bool(data.get('success'))
            if ok:
                return {
                    'success': True,
                    'response': "status=%s uid=%s" % (sms_data.get('status'), sms_data.get('uid')),
                    'error': False,
                }
            error = (data.get('message') or sms_data.get('failure_reason')
                     or response.text[:500] or "HTTP %s" % response.status_code)
            return {'success': False, 'response': response.text[:2000], 'error': error}
        except Exception as exc:  # noqa: BLE001 - any transport error must be reported, not raised
            _logger.exception("SwalaSMS request failed")
            return {'success': False, 'response': False, 'error': str(exc)}

    def test_connection(self):
        if requests is None:
            return {'success': False, 'response': False, 'error': "The 'requests' library is not available."}
        base_url = self._base_url()
        if not base_url:
            return {'success': False, 'response': False, 'error': "No API URL configured."}
        try:
            response = requests.get("%s/balance" % base_url, headers=self._headers(), timeout=10)
            try:
                data = response.json()
            except ValueError:
                data = {}
            if response.ok and data.get('success'):
                bal = data.get('data') or {}
                return {
                    'success': True,
                    'response': "Connected. Balance: %s %s" % (bal.get('balance'), bal.get('currency')),
                    'error': False,
                }
            return {
                'success': False,
                'response': response.text[:2000],
                'error': data.get('message') or "HTTP %s" % response.status_code,
            }
        except Exception as exc:  # noqa: BLE001
            return {'success': False, 'response': False, 'error': str(exc)}


class SwalaSms(models.AbstractModel):
    """Callable service: ``self.env['swala.sms'].send(phone, message)``."""
    _name = 'swala.sms'
    _description = "SwalaSMS Gateway"

    def _get_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'enabled': ICP.get_bool('swala_sms.enable'),
            'api_url': ICP.get_str('swala_sms.api_url'),
            'api_key': ICP.get_str('swala_sms.api_key'),
            'sender_id': ICP.get_str('swala_sms.sender_id'),
        }

    def _get_provider(self):
        config = self._get_config()
        if config['enabled'] and config.get('api_url') and config.get('api_key'):
            return _SwalaSmsProvider(config)
        return _TestSmsProvider(config)

    def send(self, phone, message):
        """Send ``message`` to ``phone`` through SwalaSMS (or the mock provider if SwalaSMS
        isn't enabled/configured). Never raises - always returns a result dict."""
        if not phone:
            return {'success': False, 'response': False, 'error': "No phone number given."}
        return self._get_provider().send(phone, message)

    def test_connection(self):
        """Used by the Settings 'Test Connection' button."""
        return self._get_provider().test_connection()
