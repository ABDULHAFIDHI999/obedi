# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
"""Sets up sensible accounting defaults for every company on install, without hardcoding any
chart-template-specific account/journal external IDs (those vary per fiscal localization).

Also configures the Cash/Mobile Money/Bank journals so that payments made through them (parcel
payments, and expense payments from the Expenses app) post directly to that journal's own
liquidity account instead of a separate "Outstanding Receipts/Payments" account - which is
what removes the need for a manual bank-statement reconciliation step: there is nothing left
to match, the account's balance already reflects the payment."""


def _get_or_create_account(env, company, code, name, account_type):
    account = env['account.account'].search([
        ('company_ids', 'in', company.id), ('code', '=', code),
    ], limit=1)
    if not account:
        account = env['account.account'].create({
            'code': code,
            'name': name,
            'account_type': account_type,
            'company_ids': [(6, 0, [company.id])],
        })
    return account


def _get_or_create_liquidity_journal(env, company, code, name, default_account):
    # Odoo 20 already creates a journal for every new asset_cash account, so reuse the journal
    # using that account before creating one - otherwise "Cash"/"Mobile Money" end up duplicated.
    journal = env['account.journal'].search([
        ('company_id', '=', company.id),
        '|', ('code', '=', code), ('default_account_id', '=', default_account.id),
    ], limit=1)
    if not journal:
        journal = env['account.journal'].create({
            'name': name,
            'code': code,
            'type': 'cash',
            'company_id': company.id,
            'default_account_id': default_account.id,
        })
    return journal


def _use_own_account_for_reconciliation(journal):
    """Point this journal's inbound/outbound "outstanding" account at its own liquidity
    account, so posting a payment through it needs no further bank-statement matching."""
    if not journal or not journal.default_account_id:
        return
    for line in journal.inbound_payment_method_line_ids:
        line.payment_account_id = journal.default_account_id.id
    for line in journal.outbound_payment_method_line_ids:
        line.payment_account_id = journal.default_account_id.id


def post_init_hook(env):
    for company in env['res.company'].search([]):
        revenue_account = _get_or_create_account(
            env, company, '400001', 'Parcel Transport Revenue', 'income')

        # Identify the Bank account through the Bank journal's own liquidity account, not by
        # scanning for "an" asset_cash account - once Cash/Mobile Money also exist as
        # asset_cash accounts, a plain account_type search could just as well return either
        # of those instead of the actual Bank account.
        bank_journal = env['account.journal'].search([
            ('company_id', '=', company.id), ('type', '=', 'bank'),
        ], limit=1)
        bank_account = bank_journal.default_account_id

        cash_account = _get_or_create_account(env, company, '101002', 'Cash', 'asset_cash')
        mobile_account = _get_or_create_account(
            env, company, '101003', 'Mobile Money', 'asset_cash')

        cash_journal = _get_or_create_liquidity_journal(env, company, 'CSH', 'Cash', cash_account)
        mobile_journal = _get_or_create_liquidity_journal(
            env, company, 'MOB', 'Mobile Money', mobile_account)

        for journal in (bank_journal, cash_journal, mobile_journal):
            _use_own_account_for_reconciliation(journal)

        revenue_journal = env['account.journal'].search([
            ('company_id', '=', company.id), ('type', '=', 'sale'), ('code', '=', 'PCLR'),
        ], limit=1)
        if not revenue_journal:
            revenue_journal = env['account.journal'].create({
                'name': 'Parcel Revenue',
                'code': 'PCLR',
                'type': 'sale',
                'company_id': company.id,
            })

        company.write({
            'parcel_revenue_account_id': revenue_account.id,
            'parcel_receipt_account_cash_id': cash_account.id,
            'parcel_receipt_account_mobile_id': mobile_account.id,
            'parcel_receipt_account_bank_id': bank_account.id if bank_account else False,
            'parcel_revenue_journal_id': revenue_journal.id,
        })
