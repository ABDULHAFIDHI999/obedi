import logging
from datetime import datetime, time, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

FREQUENCIES = [
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
    ('yearly', 'Yearly'),
]
GRANULARITY = {
    'daily': 'day',
    'weekly': 'week',
    'monthly': 'month',
    'quarterly': 'quarter',
    'yearly': 'year',
}
STEP = {
    'daily': relativedelta(days=1),
    'weekly': relativedelta(weeks=1),
    'monthly': relativedelta(months=1),
    'quarterly': relativedelta(months=3),
    'yearly': relativedelta(years=1),
}
STATUSES = [
    ('on_track', 'On Track'),
    ('at_risk', 'At Risk'),
    ('off_track', 'Off Track'),
]
MAX_ACHIEVEMENT = 999.0


class KpiDefinition(models.Model):
    _name = 'kpi.definition'
    _description = 'Key Performance Indicator'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char(tracking=True, help="Short unique reference, e.g. SAL-001")
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    active = fields.Boolean(default=True, tracking=True)
    description = fields.Html(translate=True)
    category_id = fields.Many2one('kpi.category', string='Category', index=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.company)
    responsible_id = fields.Many2one(
        'res.users', string='Responsible', index=True, tracking=True,
        default=lambda self: self.env.user)
    user_ids = fields.Many2many(
        'res.users', 'kpi_definition_res_users_rel', 'kpi_id', 'user_id',
        string='Contributors', help="Users allowed to see this KPI and its results.")

    # ------------------------------------------------------------------
    # Measurement & target
    # ------------------------------------------------------------------
    unit = fields.Selection([
        ('number', 'Number'),
        ('percent', 'Percentage (%)'),
        ('currency', 'Currency'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('custom', 'Custom'),
    ], default='number', required=True)
    unit_custom = fields.Char(string='Custom Unit')
    unit_label = fields.Char(compute='_compute_unit_label')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    frequency = fields.Selection(FREQUENCIES, default='monthly', required=True, tracking=True)
    target_type = fields.Selection([
        ('higher', 'Higher is better'),
        ('lower', 'Lower is better'),
    ], default='higher', required=True, string='Direction', tracking=True)
    target_value = fields.Float(string='Target', tracking=True, digits=(16, 2))
    warning_threshold = fields.Float(
        string='Warning Threshold (%)', default=80.0,
        help="Achievement (in %) under which the KPI is considered off track. "
             "Between this value and 100% it is at risk.")
    period_aggregation = fields.Selection([
        ('sum', 'Sum of periods'),
        ('avg', 'Average of periods'),
        ('last', 'Last period'),
    ], default='sum', required=True, string='Roll-up',
        help="How period results are combined over a longer range (e.g. in scorecards).")

    # ------------------------------------------------------------------
    # Automatic computation
    # ------------------------------------------------------------------
    computation_mode = fields.Selection([
        ('manual', 'Manual entry'),
        ('aggregate', 'Aggregate from model'),
        ('ratio', 'Ratio from model (%)'),
    ], default='manual', required=True, string='Computation', tracking=True)
    source_model_id = fields.Many2one(
        'ir.model', string='Source Model', ondelete='cascade',
        domain="[('transient', '=', False)]")
    source_model_name = fields.Char(related='source_model_id.model', string='Source Model Name')
    source_domain = fields.Char(string='Filter', default='[]')
    denominator_domain = fields.Char(
        string='Denominator Filter', default='[]',
        help="Ratio KPIs: value = count(Filter) / count(Denominator Filter) x 100. "
             "The Filter is applied on top of the denominator filter.")
    date_field_id = fields.Many2one(
        'ir.model.fields', string='Date Field', ondelete='cascade',
        domain="[('model_id', '=', source_model_id), ('ttype', 'in', ('date', 'datetime')), ('store', '=', True)]",
        help="Field used to filter records within each period.")
    aggregation = fields.Selection([
        ('count', 'Count'),
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
    ], default='count', string='Aggregation')
    value_field_id = fields.Many2one(
        'ir.model.fields', string='Value Field', ondelete='cascade',
        domain="[('model_id', '=', source_model_id), ('ttype', 'in', ('integer', 'float', 'monetary')), ('store', '=', True)]")
    multiplier = fields.Float(default=1.0, help="Computed value is multiplied by this factor.")
    alert_off_track = fields.Boolean(
        string='Alert when off track', default=True,
        help="Schedule a to-do activity for the responsible when a period result is off track.")

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    value_ids = fields.One2many('kpi.value', 'kpi_id', string='Results')
    value_count = fields.Integer(compute='_compute_value_count', string='# Results')
    scorecard_line_ids = fields.One2many('kpi.scorecard.line', 'kpi_id', string='Scorecard Lines')
    last_value_id = fields.Many2one('kpi.value', compute='_compute_last_value', store=True, string='Latest Result')
    last_value = fields.Float(compute='_compute_last_value', store=True, string='Latest Value', digits=(16, 2))
    last_target = fields.Float(compute='_compute_last_value', store=True, string='Latest Target', digits=(16, 2))
    last_achievement = fields.Float(compute='_compute_last_value', store=True, string='Achievement (%)', aggregator='avg')
    last_status = fields.Selection(STATUSES, compute='_compute_last_value', store=True, string='Status')
    last_date = fields.Date(compute='_compute_last_value', store=True, string='Latest Period')
    trend = fields.Selection([
        ('up', 'Improving'),
        ('flat', 'Stable'),
        ('down', 'Worsening'),
    ], compute='_compute_last_value', store=True)

    _code_company_uniq = models.Constraint(
        'unique(code, company_id)',
        'The KPI code must be unique per company.',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('unit', 'unit_custom', 'currency_id')
    def _compute_unit_label(self):
        labels = {'number': '', 'percent': '%', 'hours': 'h', 'days': 'd'}
        for kpi in self:
            if kpi.unit == 'currency':
                kpi.unit_label = kpi.currency_id.symbol or ''
            elif kpi.unit == 'custom':
                kpi.unit_label = kpi.unit_custom or ''
            else:
                kpi.unit_label = labels.get(kpi.unit, '')

    @api.depends('value_ids')
    def _compute_value_count(self):
        data = dict(self.env['kpi.value']._read_group(
            [('kpi_id', 'in', self.ids)], ['kpi_id'], ['__count']))
        for kpi in self:
            kpi.value_count = data.get(kpi, 0)

    @api.depends('value_ids.date_from', 'value_ids.actual_value', 'value_ids.target_value',
                 'value_ids.achievement', 'value_ids.status', 'target_type')
    def _compute_last_value(self):
        for kpi in self:
            values = kpi.value_ids.sorted('date_from', reverse=True)
            last = values[:1]
            kpi.last_value_id = last
            kpi.last_value = last.actual_value
            kpi.last_target = last.target_value
            kpi.last_achievement = last.achievement
            kpi.last_status = last.status
            kpi.last_date = last.date_from
            trend = False
            if len(values) >= 2:
                previous = values[1].actual_value
                if last.actual_value == previous:
                    trend = 'flat'
                else:
                    better = last.actual_value > previous
                    if kpi.target_type == 'lower':
                        better = not better
                    trend = 'up' if better else 'down'
            kpi.trend = trend

    # ------------------------------------------------------------------
    # Constraints & onchanges
    # ------------------------------------------------------------------
    @api.constrains('warning_threshold')
    def _check_warning_threshold(self):
        for kpi in self:
            if not 0 <= kpi.warning_threshold <= 100:
                raise ValidationError(self.env._("The warning threshold must be between 0 and 100%."))

    @api.constrains('computation_mode', 'source_model_id', 'date_field_id', 'aggregation', 'value_field_id')
    def _check_auto_configuration(self):
        for kpi in self.filtered(lambda k: k.computation_mode != 'manual'):
            if not kpi.source_model_id or not kpi.date_field_id:
                raise ValidationError(self.env._(
                    "KPI '%(kpi)s': a source model and a date field are required for automatic computation.",
                    kpi=kpi.name))
            if kpi.computation_mode == 'aggregate' and kpi.aggregation != 'count' and not kpi.value_field_id:
                raise ValidationError(self.env._(
                    "KPI '%(kpi)s': choose the value field to aggregate.", kpi=kpi.name))

    @api.onchange('source_model_id')
    def _onchange_source_model_id(self):
        self.date_field_id = False
        self.value_field_id = False
        self.source_domain = '[]'
        self.denominator_domain = '[]'

    @api.onchange('computation_mode')
    def _onchange_computation_mode(self):
        if self.computation_mode == 'ratio':
            self.unit = 'percent'
            self.period_aggregation = 'avg'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _calc_achievement(self, actual, target, target_type):
        """ Return achievement in % of target (capped to MAX_ACHIEVEMENT). """
        if target_type == 'lower':
            if actual <= 0:
                result = 100.0 if target >= 0 else 0.0
            else:
                result = (target / actual) * 100.0
        else:
            if not target:
                result = 100.0 if actual >= 0 else 0.0
            else:
                result = (actual / target) * 100.0
        return max(min(result, MAX_ACHIEVEMENT), 0.0)

    def _calc_status(self, achievement):
        self.ensure_one()
        if achievement >= 100.0:
            return 'on_track'
        if achievement >= self.warning_threshold:
            return 'at_risk'
        return 'off_track'

    def _get_period(self, day):
        """ Return (date_from, date_to) of the KPI period containing ``day``. """
        self.ensure_one()
        granularity = GRANULARITY[self.frequency]
        return date_utils.start_of(day, granularity), date_utils.end_of(day, granularity)

    def _iter_periods(self, date_from, date_to):
        """ Yield all (start, end) periods intersecting [date_from, date_to]. """
        self.ensure_one()
        start, _end = self._get_period(date_from)
        while start <= date_to:
            period = self._get_period(start)
            yield period
            start = period[1] + timedelta(days=1)

    def _get_eval_context(self):
        return {
            'uid': self.env.uid,
            'user': self.env.user,
            'company_id': self.company_id.id or self.env.company.id,
            'company_ids': self.env.companies.ids,
            'context_today': fields.Date.context_today,
            'datetime': datetime,
            'relativedelta': relativedelta,
        }

    def _parse_domain(self, domain_str):
        try:
            domain = safe_eval(domain_str or '[]', self._get_eval_context())
        except Exception as e:
            raise UserError(self.env._("KPI '%(kpi)s': invalid filter (%(error)s).", kpi=self.name, error=e)) from e
        return list(domain)

    def _period_domain(self, date_from, date_to):
        self.ensure_one()
        fname = self.date_field_id.name
        if self.date_field_id.ttype == 'datetime':
            return [
                (fname, '>=', datetime.combine(date_from, time.min)),
                (fname, '<', datetime.combine(date_to + timedelta(days=1), time.min)),
            ]
        return [(fname, '>=', date_from), (fname, '<=', date_to)]

    def _compute_actual(self, date_from, date_to):
        """ Compute the actual value of an automatic KPI on a period. """
        self.ensure_one()
        if self.computation_mode == 'manual':
            return 0.0
        model_name = self.source_model_id.model
        if model_name not in self.env:
            raise UserError(self.env._("Model %(model)s is not available.", model=model_name))
        Model = self.env[model_name].sudo()
        if self.company_id:
            Model = Model.with_company(self.company_id)
        period = self._period_domain(date_from, date_to)

        if self.computation_mode == 'ratio':
            base = self._parse_domain(self.denominator_domain) + period
            denominator = Model.search_count(base)
            numerator = Model.search_count(base + self._parse_domain(self.source_domain))
            value = (numerator / denominator * 100.0) if denominator else 0.0
        else:
            domain = self._parse_domain(self.source_domain) + period
            if self.aggregation == 'count':
                value = Model.search_count(domain)
            else:
                [(value,)] = Model._read_group(domain, [], [f'{self.value_field_id.name}:{self.aggregation}'])
                value = value or 0.0
        return float(value) * (self.multiplier or 1.0)

    def _compute_period_value(self, date_from, date_to):
        """ Create or update the result of the period. Returns the kpi.value. """
        self.ensure_one()
        Value = self.env['kpi.value']
        record = Value.search([('kpi_id', '=', self.id), ('date_from', '=', date_from)], limit=1)
        if self.computation_mode == 'manual':
            if not record:
                record = Value.create({
                    'kpi_id': self.id, 'date_from': date_from, 'date_to': date_to,
                    'target_value': self.target_value, 'source': 'manual',
                })
            return record
        actual = self._compute_actual(date_from, date_to)
        if record:
            if record.source == 'auto':
                record.write({'actual_value': actual})
        else:
            record = Value.create({
                'kpi_id': self.id, 'date_from': date_from, 'date_to': date_to,
                'target_value': self.target_value, 'actual_value': actual, 'source': 'auto',
            })
        return record

    def _alert_off_track(self, values):
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for value in values.filtered(lambda v: v.status == 'off_track' and v.kpi_id.alert_off_track):
            kpi = value.kpi_id
            if not kpi.responsible_id or not activity_type:
                continue
            already = kpi.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type and a.user_id == kpi.responsible_id
                and a.summary and value.name in a.summary)
            if already:
                continue
            kpi.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=self.env._("Off track: %(name)s", name=value.name),
                note=self.env._("Achievement is %(ach).1f%% (actual %(actual).2f vs target %(target).2f).",
                                ach=value.achievement, actual=value.actual_value, target=value.target_value),
                user_id=kpi.responsible_id.id,
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_compute_current(self):
        today = fields.Date.context_today(self)
        values = self.env['kpi.value']
        for kpi in self:
            values |= kpi._compute_period_value(*kpi._get_period(today))
        self._alert_off_track(values)
        return True

    def action_open_compute_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Compute KPIs'),
            'res_model': 'kpi.compute.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_kpi_ids': self.ids},
        }

    def action_view_values(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('kpi_management.action_kpi_value')
        action['domain'] = [('kpi_id', '=', self.id)]
        action['context'] = {'default_kpi_id': self.id, 'search_default_group_kpi': 0}
        return action

    @api.model
    def _cron_compute_kpis(self):
        """ Compute current and previous period of all automatic KPIs. """
        today = fields.Date.context_today(self)
        kpis = self.search([('computation_mode', '!=', 'manual')])
        for kpi in kpis:
            try:
                with self.env.cr.savepoint():
                    current_from, current_to = kpi._get_period(today)
                    prev_from, prev_to = kpi._get_period(current_from - timedelta(days=1))
                    kpi._compute_period_value(prev_from, prev_to)
                    value = kpi._compute_period_value(current_from, current_to)
                    # Alert only on closed periods to avoid noise during the period
                    prev_value = self.env['kpi.value'].search(
                        [('kpi_id', '=', kpi.id), ('date_from', '=', prev_from)], limit=1)
                    kpi._alert_off_track(prev_value)
                    _logger.debug("KPI %s computed: %s", kpi.display_name, value.actual_value)
            except Exception:
                _logger.exception("Failed to compute KPI %s (id=%s)", kpi.name, kpi.id)

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for kpi in self:
            kpi.display_name = f"[{kpi.code}] {kpi.name}" if kpi.code else (kpi.name or '')
