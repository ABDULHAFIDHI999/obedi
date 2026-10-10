# Part of AMASE Digital Demo Logistics. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request


class ParcelTrackingController(http.Controller):

    @http.route(['/track', '/track/<path:tracking_number>'], type='http', auth='public',
                website=True, sitemap=False)
    def track_parcel(self, tracking_number=None, **kwargs):
        tracking_number = tracking_number or kwargs.get('tracking_number')
        result = False
        searched = False
        if tracking_number:
            searched = True
            result = request.env['parcel.order']._tracking_lookup(tracking_number)
        return request.render('parcel_transport.website_track_page', {
            'tracking_number': tracking_number or '',
            'result': result,
            'searched': searched,
        })

    @http.route(['/agent/arrive'], type='http', auth='public', website=True, sitemap=False,
                methods=['GET', 'POST'], csrf=False)
    def agent_arrive(self, **kwargs):
        tracking_number = kwargs.get('tracking_number', '')
        agent_code = kwargs.get('agent_code', '')
        result = None
        if request.httprequest.method == 'POST':
            Order = request.env['parcel.order'].sudo()
            if kwargs.get('authorize_payment'):
                result = Order._agent_authorize_payment_submit(
                    tracking_number, agent_code,
                    kwargs.get('amount'), kwargs.get('payment_method'))
            else:
                result = Order._agent_arrive_submit(tracking_number, agent_code)
        return request.render('parcel_transport.website_agent_arrive_page', {
            'tracking_number': tracking_number,
            'agent_code': agent_code,
            'result': result,
        })

    @http.route(['/agent/receipt'], type='http', auth='public', website=False, sitemap=False, csrf=False)
    def agent_receipt(self, payment_id=None, tracking_number=None, agent_code=None, **kwargs):
        if not payment_id or not str(payment_id).isdigit():
            return request.not_found()
        payment = request.env['parcel.payment']._agent_receipt_lookup(payment_id, tracking_number, agent_code)
        if not payment:
            return request.not_found()
        pdf_content, _report_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'parcel_transport.action_report_parcel_payment', payment.ids)
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'inline; filename="%s.pdf"' % payment.name.replace('/', '_')),
        ]
        return request.make_response(pdf_content, headers=headers)
