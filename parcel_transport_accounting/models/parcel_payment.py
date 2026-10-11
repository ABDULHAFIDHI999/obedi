# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.tools.translate import _

# Which res.company receipt-account field to debit for each parcel.payment payment_method.
RECEIPT_ACCOUNT_FIELD_BY_METHOD = {
    'cash': 'parcel_receipt_account_cash_id',
    'mobile_money': 'parcel_receipt_account_mobile_id',
    'bank_transfer': 'parcel_receipt_account_bank_id',
    'card': 'parcel_receipt_account_bank_id',
    'other': 'parcel_receipt_account_bank_id',
}


class ParcelPayment(models.Model):
    _inherit = 'parcel.payment'

    account_move_id = fields.Many2one(
        'account.move', string="Journal Entry", readonly=True, copy=False,
        help="Accounting entry automatically posted for this payment.")

    # ------------------------------------------------------------------
    # Hooks: post/reverse the accounting entry alongside the existing workflow
    # ------------------------------------------------------------------
    def action_authorize(self):
        res = super().action_authorize()
        self._post_parcel_revenue_entry()
        return res

    def action_agent_authorize(self, agent):
        res = super().action_agent_authorize(agent)
        self._post_parcel_revenue_entry()
        return res

    def action_refund(self):
        res = super().action_refund()
        self._reverse_parcel_revenue_entry()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._reverse_parcel_revenue_entry()
        return res

    # ------------------------------------------------------------------
    # Accounting
    # ------------------------------------------------------------------
    def _post_parcel_revenue_entry(self):
        """Post Debit Receipt Account / Credit Parcel Revenue Account for this payment, once.
        The receipt account depends on the payment method (cash/mobile money/bank), each
        pointing to its own journal's liquidity account directly - so that account's balance
        (Cash on hand, Mobile Money, Bank) updates immediately with no reconciliation step
        needed. Never blocks the parcel payment workflow: if Accounting isn't configured yet
        (missing revenue/receipt account or journal), the payment is simply left without a
        journal entry - an administrator can configure Settings > Parcel Transport >
        Accounting and nothing else needs to change."""
        for payment in self:
            if payment.account_move_id:
                continue  # already posted - avoid duplicates
            company = payment.company_id or self.env.company
            journal = company.parcel_revenue_journal_id
            revenue_account = company.parcel_revenue_account_id
            receipt_field = RECEIPT_ACCOUNT_FIELD_BY_METHOD.get(
                payment.payment_method, 'parcel_receipt_account_bank_id')
            receipt_account = company[receipt_field] or company.parcel_receipt_account_bank_id
            if not (journal and revenue_account and receipt_account):
                continue
            move = self.env['account.move'].sudo().create({
                'move_type': 'entry',
                'journal_id': journal.id,
                'date': fields.Date.context_today(payment, timestamp=payment.payment_date),
                'ref': _("Parcel %(tracking)s - Payment %(payment)s",
                         tracking=payment.parcel_order_id.tracking_number, payment=payment.name),
                'line_ids': [
                    (0, 0, {
                        'account_id': receipt_account.id,
                        'partner_id': payment.partner_id.id,
                        'name': payment.reference or payment.name,
                        'debit': payment.amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'account_id': revenue_account.id,
                        'partner_id': payment.partner_id.id,
                        'name': payment.reference or payment.name,
                        'debit': 0.0,
                        'credit': payment.amount,
                    }),
                ],
            })
            move.sudo().action_post()
            payment.account_move_id = move.id

    def _reverse_parcel_revenue_entry(self):
        """Reverse (and fully reconcile against) the posted revenue entry, if any, when a
        payment is refunded or cancelled - so the books stay correct without anyone having to
        touch Accounting by hand. Guarded against double-reversal (e.g. refund followed by
        cancel on the same payment): if a reversal already exists for this entry, do nothing."""
        for payment in self:
            move = payment.account_move_id
            if move and move.state == 'posted' and not move.reversal_move_ids:
                move.sudo()._reverse_moves(
                    default_values_list=[{
                        'ref': _("Reversal of %s", move.name),
                    }],
                    cancel=True,
                )

    def action_view_journal_entry(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Journal Entry"),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.account_move_id.id,
        }
