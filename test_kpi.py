from datetime import date

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestKpi(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Kpi = cls.env['kpi.definition']
        cls.partner_model = cls.env['ir.model']._get('res.partner')
        cls.create_date_field = cls.env['ir.model.fields']._get('res.partner', 'create_date')

    def test_achievement_higher_is_better(self):
        self.assertAlmostEqual(self.Kpi._calc_achievement(80, 100, 'higher'), 80.0)
        self.assertAlmostEqual(self.Kpi._calc_achievement(150, 100, 'higher'), 150.0)
        self.assertAlmostEqual(self.Kpi._calc_achievement(5, 0, 'higher'), 100.0)

    def test_achievement_lower_is_better(self):
        self.assertAlmostEqual(self.Kpi._calc_achievement(50, 25, 'lower'), 50.0)
        self.assertAlmostEqual(self.Kpi._calc_achievement(20, 25, 'lower'), 125.0)
        self.assertAlmostEqual(self.Kpi._calc_achievement(0, 25, 'lower'), 100.0)

    def test_periods(self):
        kpi = self.Kpi.create({'name': 'Q', 'frequency': 'quarterly'})
        self.assertEqual(kpi._get_period(date(2026, 5, 17)), (date(2026, 4, 1), date(2026, 6, 30)))
        periods = list(kpi._iter_periods(date(2026, 2, 1), date(2026, 8, 1)))
        self.assertEqual(len(periods), 3)

    def test_manual_value_status(self):
        kpi = self.Kpi.create({'name': 'Manual', 'target_value': 100, 'warning_threshold': 80})
        value = self.env['kpi.value'].create({
            'kpi_id': kpi.id, 'date_from': date(2026, 1, 1), 'date_to': date(2026, 1, 31),
            'target_value': 100, 'actual_value': 85,
        })
        self.assertEqual(value.status, 'at_risk')
        self.assertEqual(kpi.last_status, 'at_risk')
        value.actual_value = 50
        self.assertEqual(value.status, 'off_track')

    def test_auto_count(self):
        today = fields.Datetime.now().date()
        kpi = self.Kpi.create({
            'name': 'Partners',
            'frequency': 'daily',
            'target_value': 1,
            'computation_mode': 'aggregate',
            'aggregation': 'count',
            'source_model_id': self.partner_model.id,
            'date_field_id': self.create_date_field.id,
            'source_domain': "[('name', '=like', 'KPI-TEST-%')]",
        })
        self.env['res.partner'].create([{'name': 'KPI-TEST-1'}, {'name': 'KPI-TEST-2'}])
        self.env.flush_all()
        value = kpi._compute_period_value(*kpi._get_period(today))
        self.assertEqual(value.actual_value, 2.0)
        self.assertEqual(value.status, 'on_track')

    def test_invalid_domain(self):
        kpi = self.Kpi.create({
            'name': 'Bad',
            'computation_mode': 'aggregate',
            'aggregation': 'count',
            'source_model_id': self.partner_model.id,
            'date_field_id': self.create_date_field.id,
            'source_domain': "[('name', '=',",
        })
        with self.assertRaises(UserError):
            kpi._compute_actual(date(2026, 1, 1), date(2026, 1, 31))

    def test_scorecard(self):
        kpi_a = self.Kpi.create({'name': 'A', 'target_value': 100})
        kpi_b = self.Kpi.create({'name': 'B', 'target_value': 10, 'target_type': 'lower'})
        card = self.env['kpi.scorecard'].create({
            'name': 'Card',
            'date_from': date(2026, 1, 1),
            'date_to': date(2026, 3, 31),
            'max_achievement': 120,
            'line_ids': [
                (0, 0, {'kpi_id': kpi_a.id, 'weight': 60, 'target_value': 100, 'actual_value': 150}),
                (0, 0, {'kpi_id': kpi_b.id, 'weight': 40, 'target_value': 10, 'actual_value': 20}),
            ],
        })
        # A capped at 120% -> 72 ; B = 50% -> 20 ; total 92
        self.assertAlmostEqual(card.score, 92.0, places=2)
        self.assertEqual(card.rating, 'good')

    def test_scorecard_weights(self):
        kpi = self.Kpi.create({'name': 'W', 'target_value': 1})
        card = self.env['kpi.scorecard'].create({
            'name': 'Card', 'date_from': date(2026, 1, 1), 'date_to': date(2026, 1, 31),
            'line_ids': [(0, 0, {'kpi_id': kpi.id, 'weight': 50})],
        })
        with self.assertRaises(UserError):
            card.action_start()
