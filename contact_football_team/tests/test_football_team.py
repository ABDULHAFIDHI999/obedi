from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFootballTeam(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env['football.team'].create({'name': 'Test United'})

    def test_partner_football_team(self):
        partner = self.env['res.partner'].create({
            'name': 'John Fan',
            'football_team_id': self.team.id,
        })
        self.assertEqual(partner.football_team_id, self.team)
        self.assertIn(partner, self.team.partner_ids)
        self.assertEqual(self.team.partner_count, 1)

    def test_action_view_supporters(self):
        action = self.team.action_view_supporters()
        self.assertEqual(action['res_model'], 'res.partner')
        self.assertEqual(action['domain'], [('football_team_id', '=', self.team.id)])
