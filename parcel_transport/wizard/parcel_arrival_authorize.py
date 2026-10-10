# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ParcelArrivalAuthorizeWizard(models.TransientModel):
    _name = 'parcel.arrival.authorize.wizard'
    _description = "Authorize Parcel Arrival at Destination"

    parcel_order_id = fields.Many2one('parcel.order', string="Parcel Order", required=True, readonly=True)
    tracking_number = fields.Char(related='parcel_order_id.tracking_number', readonly=True)
    sender_id = fields.Many2one(related='parcel_order_id.sender_id', readonly=True, string="Sender")
    receiver_id = fields.Many2one(related='parcel_order_id.receiver_id', readonly=True, string="Receiver")
    destination = fields.Char(related='parcel_order_id.destination', readonly=True, string="Destination")
    notes = fields.Text(string="Notes")
    proof = fields.Binary(string="Proof / Photo")
    proof_filename = fields.Char(string="Proof Filename")

    def action_authorize(self):
        self.ensure_one()
        self.parcel_order_id.action_authorize_arrival(
            notes=self.notes, proof=self.proof, proof_filename=self.proof_filename)
        return {'type': 'ir.actions.act_window_close'}
