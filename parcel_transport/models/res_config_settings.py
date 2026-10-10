# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    parcel_require_payment_before_delivery = fields.Boolean(
        string="Require payment authorization before delivery",
        config_parameter='parcel_transport.require_payment_before_delivery')
