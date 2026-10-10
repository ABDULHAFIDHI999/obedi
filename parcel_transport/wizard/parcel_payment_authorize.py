# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ParcelPaymentAuthorizeWizard(models.TransientModel):
    _name = 'parcel.payment.authorize.wizard'
    _description = "Authorize Parcel Payment"

    parcel_order_id = fields.Many2one('parcel.order', string="Parcel Order", required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    payment_method = fields.Selection([
        ('cash', "Cash"),
        ('mobile_money', "Mobile Money"),
        ('bank_transfer', "Bank Transfer"),
        ('card', "Card"),
        ('other', "Other"),
    ], string="Payment Method", default='cash', required=True)
    reference = fields.Char(string="Reference")
    notes = fields.Text(string="Notes")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order_id = self.env.context.get('default_parcel_order_id')
        if order_id:
            order = self.env['parcel.order'].browse(order_id)
            res.setdefault('partner_id', order.sender_id.id)
            res.setdefault('amount', max(order.transport_fee - order.amount_paid, 0.0))
        return res

    def action_authorize(self):
        self.ensure_one()
        payment = self.env['parcel.payment'].create({
            'parcel_order_id': self.parcel_order_id.id,
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'reference': self.reference,
            'notes': self.notes,
            'state': 'confirmed',
        })
        payment.action_authorize()
        return {'type': 'ir.actions.act_window_close'}
