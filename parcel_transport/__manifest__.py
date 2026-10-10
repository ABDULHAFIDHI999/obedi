# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
{
    'name': "Parcel Transportation Management",
    'summary': "Manage parcel transport operations on top of Odoo Inventory: receiving, dispatch, "
               "trips, destination authorization, delivery, payments, SMS notifications and public tracking.",
    'description': """
Parcel Transportation Management
=================================
A professional, lightweight parcel transportation management system for a bus/coach-based
parcel service: simple origin/destination, trips, destination authorization, payments, SMS
notifications and public tracking.

Features:
---------
* Parcel Order with automatic tracking number generation
* Trip management (bus company, agent, origin/destination, assigned parcels)
* Parcel Agents with auto-generated agent codes
* Public, login-free "Agent Receiving" form on the website (parcel number + agent code)
* Destination agent authorization workflow for arrival and delivery
* Lightweight payment tracking with authorization workflow
* SMS notifications sent through the standalone SwalaSMS Integration module (swala_sms) - any
  message sent here goes through SwalaSMS once configured there, with a mock/test provider used
  automatically until then
* SMS history log with retry support
* Public, login-free parcel tracking page on the website
* Exactly 4 role-based security groups: Administrator (full access), Receiving Officer (create,
  receive, assign to Trip, mark ready for dispatch), Dispatcher (manage/dispatch Trips, plus a
  backend fallback to authorize arrival and payment when the field agent hasn't done it on the
  website yet), Finance Manager (oversee/manage payments and the Dashboard)
* Operational dashboard with KPIs and breakdowns
* Full chatter / activity / audit trail on every key document
""",
    'version': '1.0',
    'category': 'Inventory/Delivery',
    'author': "AMASE Digital Demo Logistics",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'website',
        'swala_sms',
    ],
    'data': [
        # security
        'security/parcel_security_groups.xml',
        'security/ir.access.csv',

        # data
        'data/ir_sequence_data.xml',

        # reports (loaded before views so views can reference report actions by xmlid)
        'report/parcel_order_report.xml',
        'report/parcel_payment_report.xml',

        # views
        'views/parcel_agent_views.xml',
        'views/parcel_order_views.xml',
        'views/parcel_trip_views.xml',
        'views/parcel_payment_views.xml',
        'views/parcel_sms_history_views.xml',
        'views/res_config_settings_views.xml',
        'views/parcel_dashboard_views.xml',
        'views/parcel_menus.xml',

        # wizards
        'wizard/parcel_arrival_authorize_views.xml',
        'wizard/parcel_delivery_authorize_views.xml',
        'wizard/parcel_payment_authorize_views.xml',

        # website
        'views/website_templates.xml',
    ],
    'demo': [
        'demo/parcel_demo_company.xml',
        'demo/parcel_demo_products.xml',
        'demo/parcel_demo_partners.xml',
        'demo/parcel_demo_agents.xml',
        'demo/parcel_demo_users.xml',
        'demo/parcel_demo_orders.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'parcel_transport/static/src/js/**/*',
            'parcel_transport/static/src/xml/**/*',
            'parcel_transport/static/src/scss/dashboard.scss',
        ],
        'web.assets_frontend': [
            'parcel_transport/static/src/scss/tracking.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    # Auto-install as soon as its dependencies (base, mail, product, website) are present.
    # This guarantees the app always appears on the Apps home screen - and the website
    # homepage sections always get (re)applied - on every fresh rebuild, without anyone
    # having to manually click "Install" first.
    'auto_install': True,
}
