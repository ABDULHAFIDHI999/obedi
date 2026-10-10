# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    swala_sms_enable = fields.Boolean(
        string="Enable SwalaSMS",
        config_parameter='swala_sms.enable',
        help="When disabled (or not configured), a built-in test/mock provider is used instead, "
             "so anything sending SMS through this gateway keeps working offline.")
    swala_sms_api_url = fields.Char(
        string="SwalaSMS API Base URL", config_parameter='swala_sms.api_url')
    swala_sms_api_key = fields.Char(
        string="API Key", config_parameter='swala_sms.api_key')
    swala_sms_sender_id = fields.Char(
        string="Sender ID", config_parameter='swala_sms.sender_id')

    def swala_sms_test_connection(self):
        self.ensure_one()
        result = self.env['swala.sms'].test_connection()
        if not result.get('success'):
            raise UserError(_("Connection test failed: %s", result.get('error') or _("Unknown error")))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Connection Successful"),
                'message': result.get('response') or _("SwalaSMS is reachable."),
                'type': 'success',
                'sticky': False,
            },
        }
