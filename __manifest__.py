{
    'name': 'KPI Management',
    'version': '20.0.1.0.0',
    'category': 'Productivity',
    'sequence': 50,
    'summary': 'Define, measure and track Key Performance Indicators and scorecards',
    'description': """
KPI Management
==============
* KPI categories (Balanced Scorecard ready)
* KPIs computed manually or automatically from any Odoo model
  (count / sum / average / min / max / ratio) for daily, weekly,
  monthly, quarterly or yearly periods
* Targets, warning thresholds, achievement % and traffic-light status
* Automatic computation via scheduled action, with activities on off-track KPIs
* Weighted scorecards per user with rating and PDF report
* Dashboard (kanban), graph and pivot analysis
* Multi-company support and role based security (User / Manager)
""",
    'author': 'Abdulhafidh Ijaa',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['mail'],
    'data': [
        'security/kpi_security.xml',
        'data/kpi_category_data.xml',
        'data/ir_cron_data.xml',
        'wizard/kpi_compute_wizard_views.xml',
        'views/kpi_category_views.xml',
        'views/kpi_value_views.xml',
        'views/kpi_definition_views.xml',
        'views/kpi_scorecard_views.xml',
        'views/kpi_menus.xml',
        'report/kpi_scorecard_report.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'demo/kpi_demo.xml',
    ],
    'application': True,
    'installable': True,
}
