# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    po_type = fields.Selection([
        ('psit', 'PSIT'),
        ('atc', 'ATC'),
        ('free', 'Bebas'),
    ], string='Type PO', required=True, default='free', copy=False)


    allowed_article_types = fields.Json(compute='_compute_allowed_article_types', store=False)

    @api.depends('po_type')
    def _compute_allowed_article_types(self):
        for order in self:
            if order.po_type == 'atc':
                order.allowed_article_types = ['yes']
            elif order.po_type == 'psit':
                order.allowed_article_types = ['no']
            else:
                order.allowed_article_types = ['yes', 'no']

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

    def _get_product_catalog_domain(self):
        domain = super()._get_product_catalog_domain()
        if self.po_type == 'atc':
            domain += [('is_article', '=', 'yes')]
        elif self.po_type == 'psit':
            domain += [('is_article', '=', 'no')]
        return domain

    @api.onchange('po_type')
    def _onchange_po_type_warn(self):
        """Peringatan jika tipe PO diubah saat sudah ada lines."""
        if self.order_line:
            return {
                'warning': {
                    'title': 'Perhatian!',
                    'message': 'Mengubah Tipe PO akan mempengaruhi filter produk pada baris PO. '
                               'Pastikan produk yang dipilih sesuai dengan tipe PO baru.',
                }
            }
