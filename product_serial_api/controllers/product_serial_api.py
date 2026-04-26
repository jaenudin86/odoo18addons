# -*- coding: utf-8 -*-
import json
import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# API Key: set via environment variable PRODUCT_API_KEY or fallback to config param
API_KEY_ENV = os.environ.get('PRODUCT_API_KEY', '')


class ProductSerialApiController(http.Controller):

    # ─── helpers ────────────────────────────────────────────────────────────────

    def _json_response(self, data, status=200):
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
        }
        return request.make_response(
            json.dumps(data, ensure_ascii=False, default=str),
            headers=list(headers.items()),
            status=status,
        )

    def _error(self, message, status=400):
        return self._json_response({'success': False, 'error': message}, status)

    def _validate_api_key(self):
        """
        Validate X-API-Key header against:
        1. Env variable PRODUCT_API_KEY
        2. Odoo system parameter  product_serial_api.key
        """
        api_key_header = request.httprequest.headers.get('X-API-Key', '')
        if not api_key_header:
            return False

        # Check env variable first
        if API_KEY_ENV and api_key_header == API_KEY_ENV:
            return True

        # Fallback: check Odoo system parameter
        param_key = request.env['ir.config_parameter'].sudo().get_param(
            'product_serial_api.key', default=''
        )
        return param_key and api_key_header == param_key

    # ─── routes ─────────────────────────────────────────────────────────────────

    @http.route(
        '/api/product/serial/<string:serial_number>',
        type='http',
        auth='public',
        methods=['GET', 'OPTIONS'],
        csrf=False,
        cors='*',
    )
    def get_product_by_serial(self, serial_number, **kwargs):
        """
        GET /api/product/serial/{serial_number}

        Header:
            X-API-Key: <your_key>

        Response 200:
        {
            "success": true,
            "serial_number": "SN-001",
            "product_variant": {
                "id": 5,
                "name": "Laptop [8GB, Black]",
                "internal_ref": "LAP-001",
                "barcode": "123456789",
                "sale_price": 15000000.0,
                "cost_price": 12000000.0,
                "uom": "Unit(s)",
                "template": {
                    "id": 3,
                    "name": "Laptop",
                    "description": "...",
                    "category": "All",
                    "image_url": "/web/image/product.template/3/image_1920"
                },
                "attributes": [
                    {"attribute": "RAM",   "value": "8GB"},
                    {"attribute": "Color", "value": "Black"}
                ]
            },
            "stock_lot": {
                "id": 12,
                "lot_name": "SN-001",
                "expiration_date": null,
                "qty_available": 1.0,
                "location": "WH/Stock"
            }
        }
        """
        # CORS preflight
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({}, 200)

        # ── Auth ────────────────────────────────────────────────────────────────
        if not self._validate_api_key():
            return self._error('Unauthorized: invalid or missing X-API-Key', 401)

        if not serial_number or not serial_number.strip():
            return self._error('serial_number is required')

        serial_number = serial_number.strip()

        # ── Lookup stock.lot ────────────────────────────────────────────────────
        Lot = request.env['stock.lot'].sudo()
        lot = Lot.search([('name', '=', serial_number)], limit=1)

        if not lot:
            return self._error(
                f"Serial number '{serial_number}' not found", 404
            )

        # ── Product variant ─────────────────────────────────────────────────────
        variant = lot.product_id
        template = variant.product_tmpl_id

        # Attribute values
        attributes = []
        for ptav in variant.product_template_attribute_value_ids:
            attributes.append({
                'attribute': ptav.attribute_id.name,
                'value': ptav.product_attribute_value_id.name,
            })

        # Stock quantity available for this specific lot
        quants = request.env['stock.quant'].sudo().search([
            ('lot_id', '=', lot.id),
        ])
        qty_available = sum(quants.mapped('quantity'))
        location_names = list({q.location_id.complete_name for q in quants})

        # Image URL (public endpoint)
        image_url = f'/web/image/product.template/{template.id}/image_1920'

        data = {
            'success': True,
            'serial_number': serial_number,
            'product_variant': {
                'id': variant.id,
                'name': variant.display_name,
                'internal_ref': variant.default_code or '',
                'barcode': variant.barcode or '',
                'sale_price': variant.lst_price,
                'cost_price': variant.standard_price,
                'uom': variant.uom_id.name if variant.uom_id else '',
                'template': {
                    'id': template.id,
                    'name': template.name,
                    'description': template.description or '',
                    'category': template.categ_id.complete_name
                                 if template.categ_id else '',
                    'image_url': image_url,
                },
                'attributes': attributes,
            },
            'stock_lot': {
                'id': lot.id,
                'lot_name': lot.name,
                'expiration_date': lot.expiration_date
                                   if hasattr(lot, 'expiration_date') else None,
                'qty_available': qty_available,
                'locations': location_names,
                'company': lot.company_id.name if lot.company_id else '',
            },
        }

        return self._json_response(data)

    @http.route(
        '/api/product/serials',
        type='http',
        auth='public',
        methods=['GET', 'OPTIONS'],
        csrf=False,
        cors='*',
    )
    def search_serials(self, **kwargs):
        """
        GET /api/product/serials?q=SN-00&limit=20&offset=0

        Header:
            X-API-Key: <your_key>

        Search multiple serial numbers (partial match).
        Useful for autocomplete / listing.
        """
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({}, 200)

        if not self._validate_api_key():
            return self._error('Unauthorized: invalid or missing X-API-Key', 401)

        query = kwargs.get('q', '').strip()
        try:
            limit = max(1, min(int(kwargs.get('limit', 20)), 100))
            offset = max(0, int(kwargs.get('offset', 0)))
        except (ValueError, TypeError):
            return self._error('limit and offset must be integers')

        domain = [('name', 'ilike', query)] if query else []
        Lot = request.env['stock.lot'].sudo()
        total = Lot.search_count(domain)
        lots = Lot.search(domain, limit=limit, offset=offset, order='name asc')

        results = []
        for lot in lots:
            variant = lot.product_id
            results.append({
                'serial_number': lot.name,
                'product_variant_id': variant.id,
                'product_name': variant.display_name,
                'internal_ref': variant.default_code or '',
                'company': lot.company_id.name if lot.company_id else '',
            })

        return self._json_response({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'results': results,
        })
