# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class WooWebhookController(http.Controller):

    @http.route('/woo_connector/webhook/<int:backend_id>', type='json', auth='public', methods=['POST'], csrf=False)
    def woo_webhook(self, backend_id, **kwargs):
        """Handle incoming webhooks from WooCommerce."""
        backend = request.env['woo.backend'].sudo().browse(backend_id)
        if not backend.exists():
            return {'status': 'error', 'message': 'Invalid Backend'}

        # Get raw data
        data = json.loads(request.httprequest.data)
        topic = request.httprequest.headers.get('X-Wc-Topic')

        _logger.info("WooCommerce Webhook Received: Topic %s for Backend %s" % (topic, backend.name))

        if topic == 'order.created':
            # Trigger order import for this specific order
            # (In a real pro connector, we process the JSON directly)
            # For now, let's trigger the import logic
            wizard = request.env['woo.operation.wizard'].sudo().create({
                'backend_id': backend.id,
                'operation': 'import_order'
            })
            wizard._import_orders()

        return {'status': 'success'}
