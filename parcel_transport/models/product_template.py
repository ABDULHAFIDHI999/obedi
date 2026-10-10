# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    parcel_is_type = fields.Boolean(
        string="Usable as Parcel Type",
        help="Check this box so this product can be selected as a Parcel Type on a Parcel Order.")
