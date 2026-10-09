from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class KpiComputeWizard(models.TransientModel):
    _name = 'kpi.compute.wizard'
    _description = 'Compute KPIs over a date range'

    kpi_ids = fields.Many2many('kpi.definition', string='KPIs',
                               domain="[('computation_mode', '!=', 'manual')]")
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self) - relativedelta(months=11, day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    alert = fields.Boolean(string='Create alerts for off-track results', default=False)

    @api.model
    def default_get(self, fields):  # noqa: A002 (same signature as the ORM)
        res = super().default_get(fields)
        if 'kpi_ids' in fields and not res.get('kpi_ids') \
                and self.env.context.get('active_model') == 'kpi.definition':
            res['kpi_ids'] = [(6, 0, self.env.context.get('active_ids', []))]
        return res

    def action_compute(self):
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(self.env._("The end date cannot be before the start date."))
        kpis = self.kpi_ids or self.env['kpi.definition'].search([('computation_mode', '!=', 'manual')])
        values = self.env['kpi.value']
        for kpi in kpis:
            periods = list(kpi._iter_periods(self.date_from, self.date_to))
            if len(periods) > 1000:
                raise UserError(self.env._("Too many periods for KPI '%(kpi)s'. Reduce the range.", kpi=kpi.name))
            for date_from, date_to in periods:
                values |= kpi._compute_period_value(date_from, date_to)
        if self.alert:
            kpis._alert_off_track(values)
        action = self.env['ir.actions.act_window']._for_xml_id('kpi_management.action_kpi_value')
        action['domain'] = [('id', 'in', values.ids)]
        return action
