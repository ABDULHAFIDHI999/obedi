# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
{
    'name': "Parcel Transport Accounting",
    'summary': "Auto-post parcel revenue to Accounting as soon as a payment is authorized.",
    'description': """
Parcel Transport Accounting
============================
Bridges Parcel Transportation Management with Odoo Accounting (Invoicing):

* As soon as a parcel payment is authorized (collected), a journal entry is posted
  automatically: Debit the receipt account matching its payment method (Cash/Mobile
  Money/Bank), Credit the Parcel Revenue account.
* If a payment is later refunded or cancelled, the journal entry is reversed automatically.
* The Cash, Mobile Money and Bank journals are configured so payments through them (parcel
  payments, and expense payments from the Expenses app) need no bank-statement
  reconciliation - the balance updates immediately.
* The Parcel Revenue account, each receipt account and the Journal used are configurable in
  Settings > Parcel Transport > Accounting (sensible defaults are set up on install).
* Expenses: just use the standard Expenses app (hr_expense) - approved/posted expense
  reports already flow into Accounting on their own, nothing extra needed here. Together,
  Accounting then shows parcel revenue and expenses in one place (e.g. the Profit and Loss
  report).
""",
    'version': '1.0',
    'category': 'Inventory/Delivery',
    'author': "AMASE Digital Demo Logistics",
    'license': 'LGPL-3',
    'depends': ['parcel_transport', 'account'],
    'data': [
        'views/parcel_payment_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
}
