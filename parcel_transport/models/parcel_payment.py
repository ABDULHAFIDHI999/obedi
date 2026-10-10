# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ParcelPayment(models.Model):
    _name = 'parcel.payment'
    _description = "Parcel Payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'payment_date desc, id desc'

    name = fields.Char(string="Payment Number", required=True, copy=False, readonly=True,
                        default=lambda self: _("New"))
    parcel_order_id = fields.Many2one('parcel.order', string="Parcel Order", required=True,
                                       ondelete='cascade', index=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True, tracking=True)
    amount = fields.Monetary(string="Amount", required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    payment_method = fields.Selection([
        ('cash', "Cash"),
        ('mobile_money', "Mobile Money"),
        ('bank_transfer', "Bank Transfer"),
        ('card', "Card"),
        ('other', "Other"),
    ], string="Payment Method", default='cash', required=True)
    payment_date = fields.Datetime(string="Payment Date", default=fields.Datetime.now, required=True)
    reference = fields.Char(string="Reference")
    state = fields.Selection([
        ('draft', "Draft"),
        ('confirmed', "Confirmed"),
        ('authorized', "Authorized"),
        ('refunded', "Refunded"),
        ('cancelled', "Cancelled"),
    ], string="Status", default='draft', required=True, tracking=True)
    authorized_by = fields.Many2one('res.users', string="Authorized By", readonly=True, tracking=True)
    authorized_by_agent_id = fields.Many2one('parcel.agent', string="Authorized By Agent", readonly=True,
                                              help="Set when this payment was authorized through the "
                                                   "public self-service 'Agent Parcel Arrival' form "
                                                   "instead of the backend.")
    authorization_date = fields.Datetime(string="Authorization Date", readonly=True)
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code('parcel.payment') or _("New")
        payments = super().create(vals_list)
        for payment in payments:
            payment.parcel_order_id._compute_payment_status()
        return payments

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals or 'amount' in vals:
            self.parcel_order_id._compute_payment_status()
        return res

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_authorize(self):
        for payment in self:
            if payment.state not in ('draft', 'confirmed'):
                raise UserError(_("Only draft or confirmed payments can be authorized."))
            payment.write({
                'state': 'authorized',
                'authorized_by': self.env.user.id,
                'authorization_date': fields.Datetime.now(),
            })
            payment.parcel_order_id.message_post(
                body=_("Payment %(ref)s of %(amount)s authorized by %(user)s.",
                       ref=payment.name, amount=payment.amount, user=self.env.user.name))
            payment.parcel_order_id._send_parcel_sms('payment_received')

    def action_agent_authorize(self, agent):
        """Authorize this payment through the public, login-free 'Agent Parcel Arrival' website
        form. ``agent`` is a parcel.agent record whose code was validated by the controller."""
        for payment in self:
            if payment.state not in ('draft', 'confirmed'):
                raise UserError(_("Only draft or confirmed payments can be authorized."))
            payment.write({
                'state': 'authorized',
                'authorized_by_agent_id': agent.id,
                'authorized_by': agent.user_id.id if agent.user_id else False,
                'authorization_date': fields.Datetime.now(),
            })
            payment.parcel_order_id.message_post(
                body=_("Payment %(ref)s of %(amount)s authorized by agent %(name)s (%(code)s) via the "
                       "self-service form.",
                       ref=payment.name, amount=payment.amount, name=agent.name, code=agent.agent_code))
            payment.parcel_order_id._send_parcel_sms('payment_received')

    def action_refund(self):
        self.write({'state': 'refunded'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # ------------------------------------------------------------------
    # Public, login-free receipt printing (used by the Agent Parcel Arrival website page)
    # ------------------------------------------------------------------
    @api.model
    def _agent_receipt_lookup(self, payment_id, tracking_number, agent_code):
        """Validate a receipt print request from the public website: the agent code must be a
        real agent, and the payment must actually belong to the given tracking number. Returns
        the payment record (sudo) or an empty recordset if the request is not valid."""
        agent = self.env['parcel.agent'].sudo().search([('agent_code', '=', (agent_code or '').strip())], limit=1)
        if not agent:
            return self.browse()
        payment = self.sudo().browse(int(payment_id)).exists()
        if not payment or payment.parcel_order_id.tracking_number != (tracking_number or '').strip():
            return self.browse()
        return payment
