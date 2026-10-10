# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools.translate import _

SMS_TYPES = [
    ('received', "Parcel Received"),
    ('dispatched', "Parcel Dispatched"),
    ('arrived', "Parcel Arrived at Destination"),
    ('ready_collection', "Ready for Collection"),
    ('delivered', "Parcel Delivered"),
    ('payment_received', "Payment Received"),
    ('payment_outstanding', "Payment Outstanding"),
    ('other', "Other"),
]


class ParcelSmsHistory(models.Model):
    _name = 'parcel.sms.history'
    _description = "Parcel SMS History"
    _order = 'create_date desc'
    _rec_name = 'phone'

    parcel_order_id = fields.Many2one('parcel.order', string="Parcel Order", index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string="Recipient")
    phone = fields.Char(string="Phone Number", required=True)
    message = fields.Text(string="Message", required=True)
    date = fields.Datetime(string="Date", default=fields.Datetime.now, required=True)
    sms_type = fields.Selection(SMS_TYPES, string="Type", default='other', required=True)
    state = fields.Selection([
        ('pending', "Pending"),
        ('sent', "Sent"),
        ('failed', "Failed"),
    ], string="Status", default='pending', required=True)
    response = fields.Text(string="Provider Response")
    error_message = fields.Text(string="Error Message")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _dispatch(self):
        """Actually send the SMS for each record in self, through the SwalaSMS gateway
        (swala_sms module) - whatever message is sent here goes through SwalaSMS once it's
        configured and enabled in Settings; until then the gateway's own mock provider is used
        automatically so this keeps working."""
        SwalaSms = self.env['swala.sms']
        for sms in self:
            result = SwalaSms.send(sms.phone, sms.message)
            if result.get('success'):
                sms.write({'state': 'sent', 'response': result.get('response'), 'error_message': False})
            else:
                sms.write({'state': 'failed', 'error_message': result.get('error') or _("Unknown error"),
                           'response': result.get('response')})
        return True

    @api.model
    def send_sms(self, sms_type, phone, message, parcel_order=None, partner=None):
        """Create a history record and immediately attempt to send it. Returns the created record."""
        if not phone:
            return False
        sms = self.create({
            'parcel_order_id': parcel_order.id if parcel_order else False,
            'partner_id': partner.id if partner else False,
            'phone': phone,
            'message': message,
            'sms_type': sms_type,
        })
        sms._dispatch()
        return sms

    def action_retry(self):
        self.filtered(lambda s: s.state == 'failed')._dispatch()
        return True
