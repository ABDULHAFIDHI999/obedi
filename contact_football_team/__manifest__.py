{
    'name': 'Contact Football Team',
    'version': '20.0.1.0.0',
    'category': 'Sales/CRM',
    'sequence': 10,
    'summary': 'Add a Football Team option on contacts',
    'description': """
Contact Football Team
=====================
* Football Teams master data (name, short name, country, league, stadium, logo)
* New *Football Team* field on every contact form
* Search, filter and group contacts by football team
* Smart button on each team listing its supporters (contacts)
""",
    'author': 'Abdulhafidh Ijaa',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/football_team_data.xml',
        'views/football_team_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': True,
}
