# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools.translate import _


class ParcelAgent(models.Model):
    _name = 'parcel.agent'
    _description = "Parcel Agent"
    _inherit = ['mail.thread']
    _order = 'name'
    _rec_names_search = ['name', 'agent_code']

    name = fields.Char(string="Agent Name", required=True, tracking=True)
    agent_code = fields.Char(string="Agent Code", required=True, copy=False, readonly=True,
                              default=lambda self: _("New"), tracking=True,
                              help="Unique code given to this agent. Used on the self-service "
                                   "'Agent Receiving' form on the website to confirm a parcel pickup.")
    phone = fields.Char(string="Phone")
    station = fields.Char(string="Station / City", help="City or station this agent normally works from.")
    user_id = fields.Many2one('res.users', string="Linked User",
                               help="Optional - link this agent to a backend user account.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _agent_code_uniq = models.Constraint(
        'unique(agent_code)',
        "The agent code must be unique!",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('agent_code', _("New")) == _("New"):
                vals['agent_code'] = self.env['ir.sequence'].next_by_code('parcel.agent') or _("New")
        return super().create(vals_list)
