# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

PARCEL_STATES = [
    ('draft', "Draft"),
    ('received', "Received"),
    ('ready_dispatch', "Ready to Dispatch"),
    ('dispatched', "Dispatched"),
    ('in_transit', "In Transit"),
    ('arrived', "Arrived at Destination"),
    ('ready_collection', "Ready for Collection"),
    ('out_for_delivery', "Out for Delivery"),
    ('delivered', "Delivered"),
    ('cancelled', "Cancelled"),
    ('returned', "Returned"),
]

# Public states exposed to the (unauthenticated) website tracking page, in display order.
TRACKING_TIMELINE = [
    ('received', "Parcel Received"),
    ('dispatched', "Dispatched"),
    ('in_transit', "In Transit"),
    ('arrived', "Arrived at Destination"),
    ('ready_collection', "Ready for Collection"),
    ('delivered', "Delivered"),
]
# Which parcel states count as "reached" each timeline step being completed.
TRACKING_STEP_REACHED = {
    'received': {'received', 'ready_dispatch', 'dispatched', 'in_transit', 'arrived',
                 'ready_collection', 'out_for_delivery', 'delivered'},
    'dispatched': {'dispatched', 'in_transit', 'arrived', 'ready_collection', 'out_for_delivery', 'delivered'},
    'in_transit': {'in_transit', 'arrived', 'ready_collection', 'out_for_delivery', 'delivered'},
    'arrived': {'arrived', 'ready_collection', 'out_for_delivery', 'delivered'},
    'ready_collection': {'ready_collection', 'out_for_delivery', 'delivered'},
    'delivered': {'delivered'},
}


class ParcelOrder(models.Model):
    _name = 'parcel.order'
    _description = "Parcel Order"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _rec_names_search = ['name', 'tracking_number', 'sender_phone', 'receiver_phone']

    name = fields.Char(string="Parcel Order Number", required=True, copy=False, readonly=True,
                        default=lambda self: _("New"))
    tracking_number = fields.Char(string="Tracking Number", required=True, copy=False, readonly=True,
                                   default=lambda self: _("New"), index=True)

    sender_id = fields.Many2one('res.partner', string="Sender", required=True, tracking=True)
    sender_phone = fields.Char(string="Sender Phone", required=True)
    receiver_id = fields.Many2one('res.partner', string="Receiver", required=True, tracking=True)
    receiver_phone = fields.Char(string="Receiver Phone", required=True)

    origin = fields.Char(string="Origin", required=True, tracking=True,
                          help="City/town/office the parcel is sent from.")
    destination = fields.Char(string="Destination", required=True, tracking=True,
                               help="City/town/office the parcel is going to.")

    parcel_type_id = fields.Many2one('product.product', string="Parcel Type", required=True,
                                      domain="[('parcel_is_type', '=', True)]")
    description = fields.Text(string="Description")
    quantity = fields.Float(string="Quantity", default=1.0, required=True)
    weight = fields.Float(string="Weight (kg)")
    dimensions = fields.Char(string="Dimensions (LxWxH cm)")

    transport_fee = fields.Monetary(string="Transportation Fee", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    payment_status = fields.Selection([
        ('unpaid', "Unpaid"),
        ('partial', "Partially Paid"),
        ('paid', "Paid"),
        ('refunded', "Refunded"),
    ], string="Payment Status", default='unpaid', compute='_compute_payment_status', store=True, tracking=True)

    state = fields.Selection(PARCEL_STATES, string="Status", default='draft', required=True,
                              copy=False, tracking=True, index=True)

    trip_id = fields.Many2one('parcel.trip', string="Assigned Trip", tracking=True,
                               domain="[('state', 'in', ('draft', 'ready'))]")
    bus_company = fields.Char(string="Bus Company", related='trip_id.bus_company', store=True)
    agent_id = fields.Many2one('parcel.agent', string="Agent", related='trip_id.agent_id', store=True)

    user_id = fields.Many2one('res.users', string="Created By", default=lambda self: self.env.user,
                               readonly=True)
    expected_arrival_date = fields.Datetime(string="Expected Arrival Date")
    actual_arrival_date = fields.Datetime(string="Actual Arrival Date", readonly=True)
    delivery_date = fields.Datetime(string="Delivery Date", readonly=True)
    notes = fields.Text(string="Notes")

    received_by = fields.Many2one('res.users', string="Received By", readonly=True)
    received_date = fields.Datetime(string="Received Date", readonly=True)
    dispatched_by = fields.Many2one('res.users', string="Dispatched By", readonly=True)
    dispatch_date = fields.Datetime(string="Dispatch Date", readonly=True)

    arrival_authorized_by = fields.Many2one('res.users', string="Arrival Authorized By", readonly=True)
    arrival_authorized_by_agent_id = fields.Many2one('parcel.agent', string="Arrival Authorized By Agent",
                                                       readonly=True,
                                                       help="Set when arrival was authorized through the "
                                                            "public self-service 'Agent Parcel Arrival' "
                                                            "form instead of the backend.")
    arrival_authorization_date = fields.Datetime(string="Arrival Authorization Date", readonly=True)
    arrival_notes = fields.Text(string="Arrival Notes", readonly=True)
    arrival_proof = fields.Binary(string="Arrival Proof", readonly=True, attachment=True)
    arrival_proof_filename = fields.Char(readonly=True)

    delivery_agent_id = fields.Many2one('res.users', string="Delivery Agent", readonly=True)
    delivery_authorized_by = fields.Many2one('res.users', string="Delivery Authorized By", readonly=True)
    delivery_authorized_by_agent_id = fields.Many2one('parcel.agent', string="Delivery Authorized By Agent",
                                                        readonly=True,
                                                        help="Set when delivery was completed through the "
                                                             "public self-service 'Agent Parcel Arrival' "
                                                             "form, right after payment was authorized "
                                                             "there (payment and delivery are treated as "
                                                             "the same handover event on that form).")
    delivery_authorization_date = fields.Datetime(string="Delivery Authorization Date", readonly=True)
    delivery_proof = fields.Binary(string="Delivery Proof", readonly=True, attachment=True)
    delivery_proof_filename = fields.Char(readonly=True)

    payment_ids = fields.One2many('parcel.payment', 'parcel_order_id', string="Payments")
    sms_ids = fields.One2many('parcel.sms.history', 'parcel_order_id', string="SMS History")

    payment_count = fields.Integer(compute='_compute_counts')
    sms_count = fields.Integer(compute='_compute_counts')
    amount_paid = fields.Monetary(string="Amount Paid", compute='_compute_payment_status',
                                   currency_field='currency_id', store=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _tracking_number_uniq = models.Constraint(
        'unique(tracking_number)',
        "The tracking number must be unique!",
    )

    @api.depends('payment_ids', 'sms_ids')
    def _compute_counts(self):
        for order in self:
            order.payment_count = len(order.payment_ids)
            order.sms_count = len(order.sms_ids)

    @api.depends('payment_ids.state', 'payment_ids.amount', 'transport_fee')
    def _compute_payment_status(self):
        for order in self:
            valid_payments = order.payment_ids.filtered(lambda p: p.state == 'authorized')
            refunded = order.payment_ids.filtered(lambda p: p.state == 'refunded')
            paid_amount = sum(valid_payments.mapped('amount'))
            order.amount_paid = paid_amount
            if refunded and paid_amount <= 0:
                order.payment_status = 'refunded'
            elif order.transport_fee and paid_amount >= order.transport_fee:
                order.payment_status = 'paid'
            elif paid_amount > 0:
                order.payment_status = 'partial'
            else:
                order.payment_status = 'unpaid'

    @api.onchange('sender_id')
    def _onchange_sender_id(self):
        if self.sender_id and self.sender_id.phone:
            self.sender_phone = self.sender_id.phone or self.sender_id.mobile

    @api.onchange('receiver_id')
    def _onchange_receiver_id(self):
        if self.receiver_id and (self.receiver_id.phone or self.receiver_id.mobile):
            self.receiver_phone = self.receiver_id.phone or self.receiver_id.mobile

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code('parcel.order') or _("New")
            if vals.get('tracking_number', _("New")) == _("New"):
                code = ''.join(ch for ch in (vals.get('origin') or 'PCL') if ch.isalnum())[:3].upper() or 'PCL'
                year = fields.Date.context_today(self).year
                seq = self.env['ir.sequence'].next_by_code('parcel.order.tracking') or '00000'
                vals['tracking_number'] = "PKL/%s/%s/%s" % (code, year, seq)
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_receive(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_("Only draft parcel orders can be received."))
            order.write({
                'state': 'received',
                'received_by': self.env.user.id,
                'received_date': fields.Datetime.now(),
            })
            order.message_post(body=_("Parcel received at %s by %s.", order.origin, self.env.user.name))
            order._send_parcel_sms('received')

    def action_mark_ready_dispatch(self):
        for order in self:
            if order.state != 'received':
                raise UserError(_("Only received parcels can be marked ready to dispatch."))
            if not order.trip_id:
                raise UserError(_("Assign a Trip before marking the parcel ready to dispatch."))
            order.state = 'ready_dispatch'

    def _action_dispatch(self, trip):
        """Called by parcel.trip.action_dispatch for every eligible parcel in the trip."""
        for order in self:
            order.write({
                'state': 'dispatched',
                'dispatched_by': self.env.user.id,
                'dispatch_date': fields.Datetime.now(),
            })
            order._send_parcel_sms('dispatched')
            # No separate real-world event between leaving the dock and being on the road: the
            # order immediately moves into transit, logged as its own tracked transition.
            order.state = 'in_transit'

    def action_authorize_arrival(self, notes=False, proof=False, proof_filename=False):
        for order in self:
            if order.state != 'in_transit':
                raise UserError(_("Only parcels in transit can have their arrival authorized."))
            order.write({
                'state': 'arrived',
                'actual_arrival_date': fields.Datetime.now(),
                'arrival_authorized_by': self.env.user.id,
                'arrival_authorization_date': fields.Datetime.now(),
                'arrival_notes': notes,
                'arrival_proof': proof,
                'arrival_proof_filename': proof_filename,
            })
            order.message_post(body=_("Arrival authorized at %s by %s.", order.destination, self.env.user.name))
            # The destination agent's authorization - not the trip's own ARRIVED status - is what
            # triggers this notification, per the business requirement.
            order._send_parcel_sms('arrived')

    def action_agent_authorize_arrival(self, agent):
        """Authorize arrival through the public, login-free 'Agent Parcel Arrival' website form.
        ``agent`` is a parcel.agent record whose code was validated by the controller."""
        self.ensure_one()
        if self.state != 'in_transit':
            raise UserError(_("This parcel is not currently in transit, so its arrival cannot be authorized."))
        self.write({
            'state': 'arrived',
            'actual_arrival_date': fields.Datetime.now(),
            'arrival_authorized_by_agent_id': agent.id,
            'arrival_authorized_by': agent.user_id.id if agent.user_id else False,
            'arrival_authorization_date': fields.Datetime.now(),
        })
        self.message_post(body=_(
            "Arrival authorized at %(destination)s by agent %(name)s (%(code)s) via the self-service form.",
            destination=self.destination, name=agent.name, code=agent.agent_code))
        # The destination agent's authorization - not the trip's own ARRIVED status - is what
        # triggers this notification, per the business requirement.
        self._send_parcel_sms('arrived')

    def action_agent_complete_delivery(self, agent):
        """Complete delivery through the public 'Agent Parcel Arrival' website form. On that
        form, payment authorization and delivery are treated as a single handover event: as
        soon as the agent authorizes the receiver's payment on collection, the parcel is
        considered delivered. ``agent`` is a parcel.agent record whose code was validated by
        the controller."""
        self.ensure_one()
        if self.state not in ('arrived', 'ready_collection', 'out_for_delivery'):
            return
        self.write({
            'state': 'delivered',
            'delivery_date': fields.Datetime.now(),
            'delivery_agent_id': agent.user_id.id if agent.user_id else False,
            'delivery_authorized_by_agent_id': agent.id,
            'delivery_authorization_date': fields.Datetime.now(),
        })
        self.message_post(body=_(
            "Delivery completed by agent %(name)s (%(code)s) immediately after payment "
            "authorization via the self-service form.", name=agent.name, code=agent.agent_code))
        self._send_parcel_sms('delivered')

    def action_mark_ready_collection(self):
        for order in self:
            if order.state != 'arrived':
                raise UserError(_("Only arrived parcels can be marked ready for collection."))
            order.state = 'ready_collection'
            order._send_parcel_sms('ready_collection')

    def action_start_delivery(self):
        for order in self:
            if order.state not in ('arrived', 'ready_collection'):
                raise UserError(_("Only arrived parcels can be put out for delivery."))
            order.write({'state': 'out_for_delivery', 'delivery_agent_id': self.env.user.id})

    def action_authorize_delivery(self, notes=False, proof=False, proof_filename=False):
        require_payment = self.env['ir.config_parameter'].sudo().get_bool(
            'parcel_transport.require_payment_before_delivery')
        for order in self:
            if order.state not in ('out_for_delivery', 'arrived', 'ready_collection'):
                raise UserError(_("This parcel is not ready for delivery authorization."))
            if require_payment in ('True', True, '1', 1) and order.payment_status not in ('paid',):
                raise UserError(_(
                    "Payment must be authorized before this parcel can be delivered "
                    "(Settings > Parcel Transport > Require payment authorization before delivery)."))
            order.write({
                'state': 'delivered',
                'delivery_date': fields.Datetime.now(),
                'delivery_authorized_by': self.env.user.id,
                'delivery_authorization_date': fields.Datetime.now(),
                'delivery_proof': proof,
                'delivery_proof_filename': proof_filename,
                'notes': (order.notes or '') + ("\n" + notes if notes else ''),
            })
            order.message_post(body=_("Delivery authorized and completed by %s.", self.env.user.name))
            order._send_parcel_sms('delivered')

    def action_cancel(self):
        for order in self:
            order.state = 'cancelled'

    def action_return(self):
        for order in self:
            order.state = 'returned'

    # ------------------------------------------------------------------
    # SMS
    # ------------------------------------------------------------------
    def _get_tracking_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_str('web.base.url') or ''
        return "%s/track/%s" % (base_url, self.tracking_number)

    def _get_sms_template(self, sms_type):
        self.ensure_one()
        company = self.company_id.name or _("our company")
        tracking_url = self._get_tracking_url()
        templates = {
            'received': _(
                "Your parcel %(tracking)s has been received by %(company)s. Destination: %(destination)s. "
                "Track your parcel: %(url)s",
                tracking=self.tracking_number, company=company, destination=self.destination, url=tracking_url),
            'dispatched': _(
                "Parcel %(tracking)s has been dispatched from %(origin)s to %(destination)s. "
                "Track: %(url)s",
                tracking=self.tracking_number, origin=self.origin, destination=self.destination, url=tracking_url),
            'arrived': _(
                "Your parcel %(tracking)s has arrived at our %(destination)s destination. "
                "Please visit/await delivery from %(company)s. Track: %(url)s",
                tracking=self.tracking_number, destination=self.destination, company=company, url=tracking_url),
            'ready_collection': _(
                "Parcel %(tracking)s is ready for collection at %(destination)s. Track: %(url)s",
                tracking=self.tracking_number, destination=self.destination, url=tracking_url),
            'delivered': _(
                "Parcel %(tracking)s has been delivered. Thank you for using %(company)s. Track: %(url)s",
                tracking=self.tracking_number, company=company, url=tracking_url),
            'payment_received': _(
                "Payment received for parcel %(tracking)s. Thank you. Track: %(url)s",
                tracking=self.tracking_number, url=tracking_url),
            'payment_outstanding': _(
                "Payment is still outstanding for parcel %(tracking)s. Track: %(url)s",
                tracking=self.tracking_number, url=tracking_url),
        }
        return templates.get(sms_type, _(
            "Update on your parcel %(tracking)s. Track: %(url)s",
            tracking=self.tracking_number, url=tracking_url))

    def _send_parcel_sms(self, sms_type):
        self.ensure_one()
        # sender-facing events vs receiver-facing events
        recipient_is_sender = sms_type in ('received', 'dispatched', 'payment_received', 'payment_outstanding')
        phone = self.sender_phone if recipient_is_sender else self.receiver_phone
        partner = self.sender_id if recipient_is_sender else self.receiver_id
        message = self._get_sms_template(sms_type)
        return self.env['parcel.sms.history'].send_sms(
            sms_type, phone, message, parcel_order=self, partner=partner)

    # ------------------------------------------------------------------
    # Smart button actions
    # ------------------------------------------------------------------
    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Payments"),
            'res_model': 'parcel.payment',
            'view_mode': 'list,form',
            'domain': [('parcel_order_id', '=', self.id)],
            'context': {'default_parcel_order_id': self.id, 'default_partner_id': self.sender_id.id},
        }

    def action_view_sms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("SMS History"),
            'res_model': 'parcel.sms.history',
            'view_mode': 'list,form',
            'domain': [('parcel_order_id', '=', self.id)],
        }

    def action_view_trip(self):
        self.ensure_one()
        if not self.trip_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _("Trip"),
            'res_model': 'parcel.trip',
            'view_mode': 'form',
            'res_id': self.trip_id.id,
        }

    def action_open_arrival_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Authorize Arrival"),
            'res_model': 'parcel.arrival.authorize.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_parcel_order_id': self.id},
        }

    def action_open_payment_authorize_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Authorize Payment"),
            'res_model': 'parcel.payment.authorize.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_parcel_order_id': self.id},
        }

    def action_open_delivery_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Authorize Delivery"),
            'res_model': 'parcel.delivery.authorize.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_parcel_order_id': self.id},
        }

    # ------------------------------------------------------------------
    # Public tracking (safe, read-only projection for the website)
    # ------------------------------------------------------------------
    @api.model
    def _tracking_lookup(self, tracking_number):
        order = self.sudo().search([('tracking_number', '=', (tracking_number or '').strip())], limit=1)
        if not order:
            return False
        timeline = []
        for step_state, step_label in TRACKING_TIMELINE:
            timeline.append({
                'state': step_state,
                'label': step_label,
                'done': order.state in TRACKING_STEP_REACHED.get(step_state, set()),
            })
        return {
            'tracking_number': order.tracking_number,
            'status': dict(PARCEL_STATES).get(order.state),
            'status_key': order.state,
            'origin': order.origin,
            'destination': order.destination,
            'date_received': order.received_date,
            'expected_arrival_date': order.expected_arrival_date,
            'actual_arrival_date': order.actual_arrival_date,
            'delivery_date': order.delivery_date,
            'timeline': timeline,
        }

    # ------------------------------------------------------------------
    # Public, login-free "Agent Parcel Arrival" form (website)
    # ------------------------------------------------------------------
    @api.model
    def _agent_validate(self, tracking_number, agent_code):
        """Validate a (tracking number, agent code) pair for the public agent forms.
        Returns (order, agent, error_message); order/agent are False on error."""
        tracking_number = (tracking_number or '').strip()
        agent_code = (agent_code or '').strip()
        if not tracking_number or not agent_code:
            return False, False, _("Please fill in both the Parcel Number and your Agent Code.")

        agent = self.env['parcel.agent'].sudo().search([('agent_code', '=', agent_code)], limit=1)
        if not agent:
            return False, False, _("Agent code not recognized. Please check your code and try again.")

        order = self.sudo().search([('tracking_number', '=', tracking_number)], limit=1)
        if not order:
            return False, False, _(
                "No parcel found for number \"%s\". Please check and try again.", tracking_number)

        return order, agent, False

    @api.model
    def _agent_status_payload(self, order, agent, message=False):
        """Build the status dict shown on the public agent page: current status plus which
        self-service actions (arrival / payment authorization) are available right now."""
        arrived_states = ('arrived', 'ready_collection', 'out_for_delivery', 'delivered')
        last_payment = order.payment_ids.filtered(lambda p: p.state in ('authorized', 'refunded')).sorted(
            key=lambda p: p.id, reverse=True)[:1]
        return {
            'success': True,
            'tracking_number': order.tracking_number,
            'state': order.state,
            'status': dict(PARCEL_STATES).get(order.state),
            'origin': order.origin,
            'destination': order.destination,
            'agent_name': agent.name,
            'agent_code': agent.agent_code,
            'payment_status': order.payment_status,
            'payment_status_label': dict(order._fields['payment_status'].selection).get(order.payment_status),
            'transport_fee': order.transport_fee,
            'amount_paid': order.amount_paid,
            'outstanding': max(order.transport_fee - order.amount_paid, 0.0),
            'can_authorize_arrival': order.state == 'in_transit',
            'can_authorize_payment': order.state in arrived_states and order.payment_status != 'paid',
            'last_payment_id': last_payment.id if last_payment else False,
            'message': message,
        }

    @api.model
    def _agent_arrive_submit(self, tracking_number, agent_code):
        """Validate and process a submission of the public Agent Parcel Arrival form. If the
        parcel is in transit, this authorizes its arrival. If it has already arrived (or moved
        further along), it just returns the current status/payment-authorization page instead
        of erroring, so an agent resubmitting the same parcel+code lands on a useful page."""
        order, agent, error = self._agent_validate(tracking_number, agent_code)
        if error:
            return {'error': error}

        not_yet_in_transit = ('draft', 'received', 'ready_dispatch', 'dispatched')
        if order.state in not_yet_in_transit:
            return {'error': _(
                "Parcel %(tracking)s is not in transit yet (current status: %(status)s). "
                "It must be In Transit before its arrival can be authorized.",
                tracking=order.tracking_number, status=dict(PARCEL_STATES).get(order.state))}

        message = False
        if order.state == 'in_transit':
            order.sudo().action_agent_authorize_arrival(agent)
            message = _("Arrival authorized. The receiver has been notified.")

        return self._agent_status_payload(order, agent, message=message)

    @api.model
    def _agent_authorize_payment_submit(self, tracking_number, agent_code, amount, payment_method):
        """Validate and process a payment authorization submitted from the public Agent Parcel
        Arrival status page (used when the receiver pays the agent in cash/mobile money at
        destination on collection)."""
        order, agent, error = self._agent_validate(tracking_number, agent_code)
        if error:
            return {'error': error}

        arrived_states = ('arrived', 'ready_collection', 'out_for_delivery', 'delivered')
        if order.state not in arrived_states:
            return {'error': _(
                "Parcel %(tracking)s has not arrived yet, so payment cannot be authorized here.",
                tracking=order.tracking_number)}
        if order.payment_status == 'paid':
            return self._agent_status_payload(
                order, agent, message=_("This parcel is already fully paid."))

        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            amount_value = 0.0
        if amount_value <= 0:
            return {'error': _("Please enter a valid amount received.")}

        payment = self.env['parcel.payment'].sudo().create({
            'parcel_order_id': order.id,
            'partner_id': order.receiver_id.id,
            'amount': amount_value,
            'payment_method': payment_method or 'cash',
            'reference': _("Collected by agent %s at destination", agent.agent_code),
        })
        payment.action_agent_authorize(agent)

        # On this form, authorizing payment on collection and delivering the parcel are treated
        # as the same handover event: the agent collecting payment means the parcel is being
        # handed to the receiver right now.
        was_delivered_already = order.state == 'delivered'
        order.sudo().action_agent_complete_delivery(agent)
        if was_delivered_already:
            message = _("Payment authorized. Thank you.")
        else:
            message = _("Payment authorized and parcel marked as Delivered. Thank you.")
        return self._agent_status_payload(order, agent, message=message)

    # ------------------------------------------------------------------
    # Demo data helper - builds a full, realistic end-to-end scenario
    # (used from demo/parcel_demo_orders.xml).
    # ------------------------------------------------------------------
    @api.model
    def _create_demo_scenario(self):
        ref = self.env.ref
        Trip = self.env['parcel.trip']
        Order = self.env['parcel.order']
        Payment = self.env['parcel.payment']

        # --- Showcase parcel: ABC Trading -> XYZ Hardware, Dar -> Mbeya, full lifecycle ---
        trip1 = Trip.create({
            'origin': 'Dar es Salaam',
            'destination': 'Mbeya',
            'bus_company': 'Kilimanjaro Coach Services',
            'agent_id': ref('parcel_transport.agent_salim').id,
            'expected_arrival': fields.Datetime.now(),
        })
        order1 = Order.create({
            'sender_id': ref('parcel_transport.partner_abc_trading').id,
            'sender_phone': '+255 712 345 678',
            'receiver_id': ref('parcel_transport.partner_xyz_hardware').id,
            'receiver_phone': '+255 754 987 654',
            'origin': 'Dar es Salaam',
            'destination': 'Mbeya',
            'parcel_type_id': ref('parcel_transport.product_parcel_medium_box').id,
            'quantity': 5,
            'weight': 25,
            'dimensions': '60x40x40 cm',
            'transport_fee': 50000,
            'description': '5 Boxes of hardware supplies',
            'expected_arrival_date': fields.Datetime.now(),
        })
        order1.action_receive()
        order1.trip_id = trip1.id
        order1.action_mark_ready_dispatch()
        trip1.action_dispatch()
        trip1.action_mark_arrived()
        order1.action_authorize_arrival(notes="Parcel received in good condition.")
        payment1 = Payment.create({
            'parcel_order_id': order1.id,
            'partner_id': order1.sender_id.id,
            'amount': 50000,
            'payment_method': 'mobile_money',
            'reference': 'MPESA-DEMO-0001',
        })
        payment1.action_confirm()
        payment1.action_authorize()
        order1.action_authorize_delivery(notes="Handed to receiver at Mbeya counter.")

        # --- A parcel currently in transit ---
        trip2 = Trip.create({
            'origin': 'Dar es Salaam',
            'destination': 'Dodoma',
            'bus_company': 'Dar Express Coaches',
            'agent_id': ref('parcel_transport.agent_fatuma').id,
            'expected_arrival': fields.Datetime.now(),
        })
        order2 = Order.create({
            'sender_id': ref('parcel_transport.partner_abc_trading').id,
            'sender_phone': '+255 712 345 678',
            'receiver_id': ref('parcel_transport.partner_juma_mwenda').id,
            'receiver_phone': '+255 767 112 233',
            'origin': 'Dar es Salaam',
            'destination': 'Dodoma',
            'parcel_type_id': ref('parcel_transport.product_parcel_large_box').id,
            'quantity': 2,
            'weight': 40,
            'transport_fee': 35000,
            'description': 'Spare parts',
        })
        order2.action_receive()
        order2.trip_id = trip2.id
        order2.action_mark_ready_dispatch()
        trip2.action_dispatch()

        # --- A freshly received parcel, not yet assigned to a trip ---
        order3 = Order.create({
            'sender_id': ref('parcel_transport.partner_xyz_hardware').id,
            'sender_phone': '+255 754 987 654',
            'receiver_id': ref('parcel_transport.partner_asha_kileo').id,
            'receiver_phone': '+255 689 445 566',
            'origin': 'Mbeya',
            'destination': 'Arusha',
            'parcel_type_id': ref('parcel_transport.product_parcel_small_box').id,
            'quantity': 1,
            'weight': 5,
            'transport_fee': 20000,
            'description': 'Documents and samples',
        })
        order3.action_receive()

        # --- A brand new draft order (not yet received) ---
        Order.create({
            'sender_id': ref('parcel_transport.partner_asha_kileo').id,
            'sender_phone': '+255 689 445 566',
            'receiver_id': ref('parcel_transport.partner_juma_mwenda').id,
            'receiver_phone': '+255 767 112 233',
            'origin': 'Arusha',
            'destination': 'Dodoma',
            'parcel_type_id': ref('parcel_transport.product_parcel_envelope').id,
            'quantity': 1,
            'weight': 1,
            'transport_fee': 15000,
            'description': 'Legal documents',
        })

        # --- A cancelled order ---
        order5 = Order.create({
            'sender_id': ref('parcel_transport.partner_juma_mwenda').id,
            'sender_phone': '+255 767 112 233',
            'receiver_id': ref('parcel_transport.partner_abc_trading').id,
            'receiver_phone': '+255 712 345 678',
            'origin': 'Dodoma',
            'destination': 'Dar es Salaam',
            'parcel_type_id': ref('parcel_transport.product_parcel_pallet').id,
            'quantity': 1,
            'weight': 80,
            'transport_fee': 60000,
            'description': 'Cancelled by customer request',
        })
        order5.action_receive()
        order5.action_cancel()
