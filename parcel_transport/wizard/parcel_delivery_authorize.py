# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ParcelDeliveryAuthorizeWizard(models.TransientModel):
    _name = 'parcel.delivery.authorize.wizard'
    _description = "Authorize Parcel Delivery"

    parcel_order_id = fields.Many2one('parcel.order', string="Parcel Order", required=True, readonly=True)
    tracking_number = fields.Char(related='parcel_order_id.tracking_number', readonly=True)
    receiver_id = fields.Many2one(related='parcel_order_id.receiver_id', readonly=True, string="Receiver")
    receiver_phone = fields.Char(related='parcel_order_id.receiver_phone', readonly=True)
    payment_status = fields.Selection(related='parcel_order_id.payment_status', readonly=True)
    notes = fields.Text(string="Delivery Notes")
    proof = fields.Binary(string="Proof of Delivery")
    proof_filename = fields.Char(string="Proof Filename")

    def action_authorize(self):
        self.ensure_one()
        self.parcel_order_id.action_authorize_delivery(
            notes=self.notes, proof=self.proof, proof_filename=self.proof_filename)
        return {'type': 'ir.actions.act_window_close'}
