# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ParcelTrip(models.Model):
    _name = 'parcel.trip'
    _description = "Parcel Trip"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'departure_date desc, id desc'

    name = fields.Char(string="Trip Number", required=True, copy=False, readonly=True,
                        default=lambda self: _("New"))
    origin = fields.Char(string="Origin", required=True, tracking=True)
    destination = fields.Char(string="Destination", required=True, tracking=True)
    bus_company = fields.Char(string="Bus Company", tracking=True,
                               help="Name of the bus/coach company operating this trip.")
    agent_id = fields.Many2one('parcel.agent', string="Agent", tracking=True,
                                help="The company agent accompanying/handling this trip (we transport by "
                                     "public bus, not owned vehicles - this is our staff, not a driver).")
    departure_date = fields.Datetime(string="Departure Date", tracking=True)
    expected_arrival = fields.Datetime(string="Expected Arrival")
    actual_arrival = fields.Datetime(string="Actual Arrival", readonly=True)
    state = fields.Selection([
        ('draft', "Draft"),
        ('ready', "Ready"),
        ('dispatched', "Dispatched"),
        ('in_transit', "In Transit"),
        ('arrived', "Arrived"),
        ('closed', "Closed"),
    ], string="Status", default='draft', required=True, tracking=True)
    parcel_ids = fields.One2many('parcel.order', 'trip_id', string="Parcels")
    parcel_count = fields.Integer(string="Parcel Count", compute='_compute_parcel_count')
    dispatch_agent_id = fields.Many2one('res.users', string="Dispatch Agent", readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('parcel_ids')
    def _compute_parcel_count(self):
        for trip in self:
            trip.parcel_count = len(trip.parcel_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code('parcel.trip') or _("New")
        return super().create(vals_list)

    def action_set_ready(self):
        for trip in self:
            if not trip.parcel_ids:
                raise UserError(_("Assign at least one parcel to the trip before marking it ready."))
            trip.state = 'ready'

    def action_dispatch(self):
        for trip in self:
            if trip.state not in ('draft', 'ready'):
                raise UserError(_("Only draft or ready trips can be dispatched."))
            if not trip.parcel_ids:
                raise UserError(_("Cannot dispatch a trip without parcels."))
            trip.write({
                'state': 'in_transit',
                'departure_date': trip.departure_date or fields.Datetime.now(),
                'dispatch_agent_id': self.env.user.id,
            })
            trip.message_post(body=_("Trip dispatched by %s.", self.env.user.name))
            trip.parcel_ids.filtered(lambda p: p.state in ('received', 'ready_dispatch'))._action_dispatch(trip)

    def action_mark_arrived(self):
        for trip in self:
            if trip.state != 'in_transit':
                raise UserError(_("Only trips in transit can be marked as arrived."))
            trip.write({'state': 'arrived', 'actual_arrival': fields.Datetime.now()})
            trip.message_post(body=_(
                "Vehicle physically arrived at %s. Awaiting destination agent authorization per parcel.",
                trip.destination))

    def action_close(self):
        for trip in self:
            open_parcels = trip.parcel_ids.filtered(
                lambda p: p.state not in ('delivered', 'cancelled', 'returned'))
            if open_parcels:
                raise UserError(_(
                    "Cannot close this trip: %d parcel(s) are not yet delivered/cancelled/returned.",
                    len(open_parcels)))
            trip.state = 'closed'

    def action_view_parcels(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('parcel_transport.action_parcel_order')
        action['domain'] = [('trip_id', '=', self.id)]
        action['context'] = {'default_trip_id': self.id}
        return action
