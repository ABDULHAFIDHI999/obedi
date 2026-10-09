from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from .kpi_definition import STATUSES


class KpiScorecard(models.Model):
    _name = 'kpi.scorecard'
    _description = 'KPI Scorecard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(required=True, tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Evaluated User', required=True, index=True, tracking=True,
        default=lambda self: self.env.user)
    reviewer_id = fields.Many2one('res.users', string='Reviewer', index=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company)
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)
    line_ids = fields.One2many('kpi.scorecard.line', 'scorecard_id', string='KPIs', copy=True)
    max_achievement = fields.Float(
        string='Achievement Cap (%)', default=120.0,
        help="Achievement above this value is not rewarded further in the score.")
    total_weight = fields.Float(compute='_compute_score', store=True)
    score = fields.Float(compute='_compute_score', store=True, string='Score (%)', aggregator='avg', tracking=True)
    rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], compute='_compute_score', store=True)
    note = fields.Html(string='Comments')

    @api.depends('line_ids.weight', 'line_ids.weighted_score')
    def _compute_score(self):
        for card in self:
            total = sum(card.line_ids.mapped('weight'))
            card.total_weight = total
            card.score = (sum(card.line_ids.mapped('weighted_score')) / total * 100.0) if total else 0.0
            if not card.line_ids:
                card.rating = False
            elif card.score >= 100:
                card.rating = 'excellent'
            elif card.score >= 85:
                card.rating = 'good'
            elif card.score >= 70:
                card.rating = 'fair'
            else:
                card.rating = 'poor'

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for card in self:
            if card.date_to < card.date_from:
                raise ValidationError(self.env._("The end date cannot be before the start date."))

    def _check_weights(self):
        for card in self:
            if not card.line_ids:
                raise UserError(self.env._("Add at least one KPI to the scorecard."))
            if float_compare(card.total_weight, 100.0, precision_digits=2):
                raise UserError(self.env._(
                    "The weights of scorecard '%(name)s' must total 100 (currently %(total).2f).",
                    name=card.name, total=card.total_weight))

    def action_start(self):
        self._check_weights()
        self.action_refresh()
        self.write({'state': 'in_progress'})

    def action_refresh(self):
        self.line_ids._refresh_from_results()
        return True

    def action_done(self):
        self._check_weights()
        self.action_refresh()
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def unlink(self):
        if any(card.state == 'done' for card in self):
            raise UserError(self.env._("A completed scorecard cannot be deleted. Cancel it first."))
        return super().unlink()


class KpiScorecardLine(models.Model):
    _name = 'kpi.scorecard.line'
    _description = 'KPI Scorecard Line'
    _order = 'sequence, id'

    scorecard_id = fields.Many2one('kpi.scorecard', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='scorecard_id.company_id', store=True, index=True)
    sequence = fields.Integer(default=10)
    kpi_id = fields.Many2one('kpi.definition', string='KPI', required=True, index=True)
    unit_label = fields.Char(related='kpi_id.unit_label')
    weight = fields.Float(default=10.0, digits=(16, 2))
    target_value = fields.Float(string='Target', digits=(16, 2))
    actual_value = fields.Float(string='Actual', digits=(16, 2))
    achievement = fields.Float(compute='_compute_achievement', store=True, string='Achievement (%)')
    weighted_score = fields.Float(compute='_compute_achievement', store=True, digits=(16, 4))
    status = fields.Selection(STATUSES, compute='_compute_achievement', store=True)
    comment = fields.Char()

    @api.depends('actual_value', 'target_value', 'weight', 'kpi_id.target_type',
                 'kpi_id.warning_threshold', 'scorecard_id.max_achievement')
    def _compute_achievement(self):
        for line in self:
            kpi = line.kpi_id
            if not kpi:
                line.achievement = line.weighted_score = 0.0
                line.status = False
                continue
            line.achievement = kpi._calc_achievement(line.actual_value, line.target_value, kpi.target_type)
            cap = line.scorecard_id.max_achievement or 100.0
            line.weighted_score = min(line.achievement, cap) / 100.0 * line.weight
            line.status = kpi._calc_status(line.achievement)

    @api.onchange('kpi_id')
    def _onchange_kpi_id(self):
        if self.kpi_id:
            self._refresh_from_results()

    def _refresh_from_results(self):
        """ Fill actual / target from the KPI results within the scorecard range. """
        for line in self:
            card = line.scorecard_id
            if not line.kpi_id or not card.date_from or not card.date_to:
                continue
            values = self.env['kpi.value'].search([
                ('kpi_id', '=', line.kpi_id.id),
                ('date_from', '>=', card.date_from),
                ('date_to', '<=', card.date_to),
            ], order='date_from')
            if not values:
                if not line.target_value:
                    line.target_value = line.kpi_id.target_value
                continue
            mode = line.kpi_id.period_aggregation
            actuals = values.mapped('actual_value')
            targets = values.mapped('target_value')
            if mode == 'sum':
                line.actual_value, line.target_value = sum(actuals), sum(targets)
            elif mode == 'avg':
                line.actual_value, line.target_value = sum(actuals) / len(actuals), sum(targets) / len(targets)
            else:
                line.actual_value, line.target_value = actuals[-1], targets[-1]
