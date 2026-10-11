# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # NOTE: domains are redeclared here (instead of inherited from the res.company field)
    # because the inherited domain string uses "id" to mean "this record's id", which on
    # res.company's own form is the company - but here, on this transient settings wizard,
    # "id" would wrongly resolve to the wizard's own id instead of the company's.
    parcel_revenue_account_id = fields.Many2one(
        related='company_id.parcel_revenue_account_id', readonly=False,
        string="Parcel Revenue Account",
        domain="[('account_type', '=', 'income'), ('company_ids', 'in', company_id)]")
    parcel_revenue_journal_id = fields.Many2one(
        related='company_id.parcel_revenue_journal_id', readonly=False,
        string="Parcel Revenue Journal",
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]")
    parcel_receipt_account_cash_id = fields.Many2one(
        related='company_id.parcel_receipt_account_cash_id', readonly=False,
        string="Cash Receipt Account",
        domain="[('account_type', '=', 'asset_cash'), ('company_ids', 'in', company_id)]")
    parcel_receipt_account_mobile_id = fields.Many2one(
        related='company_id.parcel_receipt_account_mobile_id', readonly=False,
        string="Mobile Money Receipt Account",
        domain="[('account_type', '=', 'asset_cash'), ('company_ids', 'in', company_id)]")
    parcel_receipt_account_bank_id = fields.Many2one(
        related='company_id.parcel_receipt_account_bank_id', readonly=False,
        string="Bank Receipt Account",
        domain="[('account_type', '=', 'asset_cash'), ('company_ids', 'in', company_id)]")
