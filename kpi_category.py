from odoo import api, fields, models


class KpiCategory(models.Model):
    _name = 'kpi.category'
    _description = 'KPI Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    company_id = fields.Many2one('res.company', string='Company', index=True)
    kpi_ids = fields.One2many('kpi.definition', 'category_id', string='KPIs')
    kpi_count = fields.Integer(compute='_compute_kpi_count', string='# KPIs')

    _name_company_uniq = models.Constraint(
        'unique(name, company_id)',
        'A KPI category with this name already exists.',
    )

    @api.depends('kpi_ids')
    def _compute_kpi_count(self):
        data = dict(self.env['kpi.definition']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count']))
        for category in self:
            category.kpi_count = data.get(category, 0)

    def action_view_kpis(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('kpi_management.action_kpi_definition')
        action['domain'] = [('category_id', '=', self.id)]
        action['context'] = {'default_category_id': self.id}
        return action
