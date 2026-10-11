# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    parcel_revenue_account_id = fields.Many2one(
        'account.account', string="Parcel Revenue Account",
        domain="[('account_type', '=', 'income'), ('company_ids', 'in', id)]",
        help="Income account credited whenever a parcel payment is authorized.")
    parcel_revenue_journal_id = fields.Many2one(
        'account.journal', string="Parcel Revenue Journal",
        domain="[('type', '=', 'sale'), ('company_id', '=', id)]",
        help="Journal used to post parcel revenue entries.")

    # One receipt (liquidity) account per payment method, so Cash/Mobile Money/Bank balances
    # each reflect their own money immediately - no bank statement reconciliation needed,
    # since these journals' outstanding accounts are configured to be their own liquidity
    # account (see parcel_transport_accounting/hooks.py).
    parcel_receipt_account_cash_id = fields.Many2one(
        'account.account', string="Cash Receipt Account",
        domain="[('account_type', '=', 'asset_cash'), ('company_ids', 'in', id)]",
        help="Account debited when a parcel payment is collected in cash.")
    parcel_receipt_account_mobile_id = fields.Many2one(
        'account.account', string="Mobile Money Receipt Account",
        domain="[('account_type', '=', 'asset_cash'), ('company_ids', 'in', id)]",
        help="Account debited when a parcel payment is collected via mobile money.")
    parcel_receipt_account_bank_id = fields.Many2one(
        'account.account', string="Bank Receipt Account",
        domain="[('account_type', '=', 'asset_cash'), ('company_ids', 'in', id)]",
        help="Account debited when a parcel payment is collected by bank transfer or card.")
