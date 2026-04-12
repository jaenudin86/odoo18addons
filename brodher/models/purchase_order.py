# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    po_type = fields.Selection([
        ('psit', 'PSIT'),
        ('atc', 'ATC'),
        ('free', 'Bebas'),
    ], string='Tipe PO', required=True, default='free', copy=False,
       states={'purchase': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    product_domain = fields.Json(compute='_compute_product_domain', store=False)

    @api.depends('po_type')
    def _compute_product_domain(self):
        for order in self:
            if order.po_type == 'psit':
                order.product_domain = [('is_article', '=', 'no')]
            elif order.po_type == 'atc':
                order.product_domain = [('is_article', '=', 'yes')]
            else:
                order.product_domain = []

    @api.model_create_multi
    def create(self, vals_list):
        seq_map = {
            'psit': 'purchase.order.psit',
            'atc': 'purchase.order.atc',
            'free': 'purchase.order.free',
        }
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                po_type = vals.get('po_type', 'free')
                seq_code = seq_map.get(po_type, 'purchase.order.free')
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or 'New'
        return super().create(vals_list)

    @api.onchange('po_type')
    def _onchange_po_type_clear_lines(self):
        """Peringatan jika tipe PO diubah saat sudah ada lines."""
        if self.order_line:
            return {
                'warning': {
                    'title': 'Perhatian!',
                    'message': 'Mengubah Tipe PO akan mempengaruhi filter produk pada baris PO. '
                               'Pastikan produk yang dipilih sesuai dengan tipe PO baru.',
                }
            }
