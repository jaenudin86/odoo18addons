# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    po_type = fields.Selection([
        ('psit', 'PSIT'),
        ('atc', 'ATC'),
        ('other', 'Bebas'),
    ], string='Type PO', required=True, default='other', copy=False)

    warehouse_id = fields.Many2one(
        'stock.warehouse', 
        string='Warehouse',
        default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
    )



    picking_type_id = fields.Many2one(
        'stock.picking.type',
        domain="[('code', '=', 'incoming'), ('operation_category', '=', po_type)]",
        check_company=True
    )



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
            'other': 'purchase.order.free',
        }
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                po_type = vals.get('po_type', 'other')

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

    @api.onchange('po_type', 'warehouse_id')
    def _onchange_po_type_picking_type(self):
        """Otomatis set Operation Type (Deliver To) berdasarkan Type PO."""
        if not self.po_type or not self.warehouse_id:
            return
        
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id', '=', self.warehouse_id.id),
            ('operation_category', '=', self.po_type),
        ], limit=1)

        
        if picking_type:
            self.picking_type_id = picking_type

    @api.onchange('po_type')
    def _onchange_po_type_warn(self):
        """Peringatan jika tipe PO diubah saat sudah ada lines."""
        self._onchange_po_type_picking_type()  # Panggil otomasi picking type
        if self.order_line:
            return {
                'warning': {
                    'title': 'Perhatian!',
                    'message': 'Mengubah Type PO akan mempengaruhi filter produk pada baris PO dan Operation Type. '
                               'Pastikan produk yang dipilih sesuai dengan tipe PO baru.',
                }
            }

