from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .kpi_definition import STATUSES


class KpiValue(models.Model):
    _name = 'kpi.value'
    _description = 'KPI Result'
    _order = 'date_from desc, kpi_id'
    _rec_name = 'name'

    name = fields.Char(compute='_compute_name', store=True)
    kpi_id = fields.Many2one('kpi.definition', string='KPI', required=True, index=True, ondelete='cascade')
    category_id = fields.Many2one(related='kpi_id.category_id', store=True, index=True)
    responsible_id = fields.Many2one(related='kpi_id.responsible_id', store=True, index=True)
    company_id = fields.Many2one(related='kpi_id.company_id', store=True, index=True)
    frequency = fields.Selection(related='kpi_id.frequency')
    unit_label = fields.Char(related='kpi_id.unit_label')
    date_from = fields.Date(string='Period Start', required=True, index=True)
    date_to = fields.Date(string='Period End', required=True)
    period_label = fields.Char(compute='_compute_name', store=True, string='Period')
    actual_value = fields.Float(string='Actual', digits=(16, 2), aggregator='sum')
    target_value = fields.Float(string='Target', digits=(16, 2), aggregator='sum')
    variance = fields.Float(compute='_compute_achievement', store=True, digits=(16, 2), aggregator='sum')
    achievement = fields.Float(compute='_compute_achievement', store=True, string='Achievement (%)', aggregator='avg')
    status = fields.Selection(STATUSES, compute='_compute_achievement', store=True, index=True)
    source = fields.Selection([
        ('manual', 'Manual'),
        ('auto', 'Computed'),
    ], default='manual', required=True,
        help="Computed results are refreshed by the scheduler; switch to Manual to freeze a value.")
    note = fields.Text()

    _kpi_period_uniq = models.Constraint(
        'unique(kpi_id, date_from)',
        'A result already exists for this KPI and period.',
    )

    @api.depends('kpi_id.name', 'kpi_id.frequency', 'date_from')
    def _compute_name(self):
        for value in self:
            label = value._format_period()
            value.period_label = label
            value.name = f"{value.kpi_id.name or ''} - {label}" if label else (value.kpi_id.name or '')

    def _format_period(self):
        self.ensure_one()
        day = self.date_from
        if not day:
            return ''
        frequency = self.kpi_id.frequency
        if frequency == 'yearly':
            return str(day.year)
        if frequency == 'quarterly':
            return f"Q{(day.month - 1) // 3 + 1} {day.year}"
        if frequency == 'monthly':
            return day.strftime('%m/%Y')
        if frequency == 'weekly':
            iso = day.isocalendar()
            return f"W{iso[1]:02d} {iso[0]}"
        return fields.Date.to_string(day)

    @api.depends('actual_value', 'target_value', 'kpi_id.target_type', 'kpi_id.warning_threshold')
    def _compute_achievement(self):
        for value in self:
            kpi = value.kpi_id
            if not kpi:
                value.achievement = value.variance = 0.0
                value.status = False
                continue
            value.achievement = kpi._calc_achievement(value.actual_value, value.target_value, kpi.target_type)
            value.variance = value.actual_value - value.target_value
            value.status = kpi._calc_status(value.achievement)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for value in self:
            if value.date_to < value.date_from:
                raise ValidationError(self.env._("The period end cannot be before its start."))

    @api.onchange('kpi_id', 'date_from')
    def _onchange_period(self):
        if self.kpi_id and self.date_from:
            self.date_from, self.date_to = self.kpi_id._get_period(self.date_from)
            if not self.target_value:
                self.target_value = self.kpi_id.target_value

    def action_recompute(self):
        for value in self.filtered(lambda v: v.kpi_id.computation_mode != 'manual'):
            value.write({
                'actual_value': value.kpi_id._compute_actual(value.date_from, value.date_to),
                'source': 'auto',
            })
        return True
