# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
{
    'name': "SwalaSMS Integration",
    'summary': "Generic SwalaSMS gateway connector, reusable by any module that needs to send SMS.",
    'description': """
SwalaSMS Integration
=====================
A small, standalone connector module for the "SwalaSMS" gateway (https://swalasms.com), a
Tanzanian bulk SMS provider with a documented REST API (Bearer token auth, JSON payloads).

Any other module can send an SMS through SwalaSMS by calling::

    result = self.env['swala.sms'].send(phone, message)
    # result = {'success': bool, 'response': str, 'error': str or False}

Credentials (API Base URL, API Key, Sender ID) are configured once in Settings, independently
of whatever module is actually sending the message. When SwalaSMS is disabled or not
configured, a built-in mock/test provider is used automatically instead, so callers keep
working (and keep getting a well-formed result dict) without real credentials - this is what
the "Test Connection" button in Settings also exercises (it checks the account's SMS balance).

This module does not keep its own log of sent messages - that is the responsibility of
whichever module calls it. It only owns: credentials, the enable/disable switch, and the
actual HTTP call to the real SwalaSMS API endpoints
(POST /sms/messages to send, GET /balance to check connectivity/credit).
""",
    'version': '1.0',
    'category': 'Technical',
    'author': "AMASE Digital Demo Logistics",
    'license': 'LGPL-3',
    'depends': [
        'base',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
