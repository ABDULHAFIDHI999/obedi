from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    football_team_id = fields.Many2one(
        'football.team',
        string='Football Team',
        index=True,
        ondelete='set null',
        tracking=True,
        help='Football team supported by this contact.',
    )
