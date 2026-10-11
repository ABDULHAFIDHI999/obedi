# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.tools.translate import _

# Keep in sync with the events actually triggered in parcel_order.py / parcel_payment.py.
SMS_EVENT_TYPES = [
    ('received', "Parcel Received"),
    ('arrived', "Parcel Arrived at Destination"),
    ('ready_collection', "Ready for Collection"),
    ('delivered', "Parcel Delivered"),
    ('payment_received', "Payment Received"),
]


class _SafeDict(dict):
    """Leaves an unknown {placeholder} as-is instead of raising, so a typo in a template body
    never breaks the parcel workflow - it just shows up visibly in the sent message."""

    def __missing__(self, key):
        return '{%s}' % key


class ParcelMessageTemplate(models.Model):
    _name = 'parcel.message.template'
    _description = "Parcel Message Template"
    _order = 'sequence, id'
    _rec_name = 'sms_type'

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    sms_type = fields.Selection(SMS_EVENT_TYPES, string="Event", required=True)
    recipient = fields.Selection([
        ('sender', "Sender"),
        ('receiver', "Receiver"),
    ], string="Recipient", required=True, default='receiver',
        help="Who receives the SMS/WhatsApp notification when this event happens.")
    body = fields.Text(
        string="Message", required=True,
        help="Available placeholders: {tracking}, {company}, {origin}, {destination}, {url}")

    _sms_type_uniq = models.Constraint('unique(sms_type)', "Only one template is allowed per event.")

    def _render(self, order):
        """Render this template's body for a given parcel.order record. Never raises: an
        unknown or malformed placeholder is left visible in the output rather than blocking
        the notification (and, in turn, the parcel workflow)."""
        self.ensure_one()
        values = _SafeDict(
            tracking=order.tracking_number or '',
            company=order.company_id.name or _("our company"),
            origin=order.origin or '',
            destination=order.destination or '',
            url=order._get_tracking_url(),
        )
        try:
            return self.body.format_map(values)
        except (ValueError, IndexError):
            return self.body
