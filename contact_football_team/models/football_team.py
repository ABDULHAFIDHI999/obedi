from odoo import api, fields, models


class FootballTeam(models.Model):
    _name = 'football.team'
    _description = 'Football Team'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    short_name = fields.Char(string='Short Name')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    logo = fields.Image(max_width=256, max_height=256)
    country_id = fields.Many2one('res.country', string='Country')
    league = fields.Char()
    stadium = fields.Char()
    founded_year = fields.Integer(string='Founded')
    website = fields.Char()
    note = fields.Text(string='Notes')
    partner_ids = fields.One2many('res.partner', 'football_team_id', string='Supporters')
    partner_count = fields.Integer(string='Supporters Count', compute='_compute_partner_count')

    _name_uniq = models.Constraint(
        'unique(name)',
        'A football team with this name already exists.',
    )

    @api.depends('partner_ids')
    def _compute_partner_count(self):
        groups = self.env['res.partner']._read_group(
            [('football_team_id', 'in', self.ids)],
            ['football_team_id'],
            ['__count'],
        )
        counts = {team.id: count for team, count in groups}
        for team in self:
            team.partner_count = counts.get(team.id, 0)

    def action_view_supporters(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Supporters'),
            'res_model': 'res.partner',
            'view_mode': 'list,kanban,form',
            'domain': [('football_team_id', '=', self.id)],
            'context': {'default_football_team_id': self.id},
        }
