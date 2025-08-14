from odoo import http
from odoo.http import request

class BarcodeScanController(http.Controller):

    @http.route('/scan_barcode', type='http', auth='user', website=True)
    def scan_barcode_form(self, **kwargs):
        return request.render('brodher.scan_barcode_template', {})

    @http.route('/scan_barcode/result', type='http', auth='user', website=True, methods=['POST'])
    def scan_barcode_result(self, **post):
        barcode = post.get('barcode')
        product = request.env['product.template'].sudo().search([('barcode', '=', barcode)], limit=1)

        return request.render('brodher.scan_barcode_template', {
            'product': product,
            'barcode': barcode,
        })
