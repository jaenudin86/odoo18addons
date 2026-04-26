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

    def _get_product_catalog_domain(self):
        domain = super()._get_product_catalog_domain()
        if self.po_type == 'atc':
            domain += [('is_article', '=', 'yes')]
        elif self.po_type == 'psit':
            domain += [('is_article', '=', 'no')]
        return domain

    @api.onchange('partner_id', 'po_type', 'warehouse_id')

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

    @api.model_create_multi
    def create(self, vals_list):
        seq_map = {
            'psit': 'purchase.order.psit',
            'atc': 'purchase.order.atc',
            'other': 'purchase.order.free',
        }
        for vals in vals_list:
            # 1. Handle Sequence
            if vals.get('name', 'New') == 'New':
                po_type = vals.get('po_type', 'other')
                seq_code = seq_map.get(po_type, 'purchase.order.free')
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or 'New'
            
            # 2. Ensure Correct Picking Type
            if 'picking_type_id' not in vals or not vals.get('picking_type_id'):
                warehouse_id = vals.get('warehouse_id') or self.default_get(['warehouse_id']).get('warehouse_id')
                po_type = vals.get('po_type', 'other')
                if warehouse_id:
                    picking_type = self.env['stock.picking.type'].search([
                        ('code', '=', 'incoming'),
                        ('warehouse_id', '=', warehouse_id),
                        ('operation_category', '=', po_type),
                    ], limit=1)
                    if picking_type:
                        vals['picking_type_id'] = picking_type.id

        orders = super().create(vals_list)
        orders._merge_duplicate_lines()
        return orders


    def _merge_duplicate_lines(self):
        """Menggabungkan baris PO yang memiliki produk yang sama."""
        for order in self:
            # Gunakan dict untuk melacak produk yang sudah ada di baris PO
            # Key: product_id, Value: record purchase.order.line
            seen_products = {}
            lines_to_remove = self.env['purchase.order.line']
            
            for line in order.order_line:
                # Kita hanya menggabungkan jika produknya sama dan bukan baris catatan/seksi
                if not line.product_id:
                    continue
                
                # Gunakan tuple (product_id, price_unit) jika ingin harga yang berbeda tidak digabung
                # Di sini kita gabung berdasarkan product_id saja sesuai permintaan
                key = line.product_id.id
                
                if key in seen_products:
                    existing_line = seen_products[key]
                    # Tambahkan qty ke baris yang sudah ada
                    existing_line.product_qty += line.product_qty
                    # Tandai baris ini untuk dihapus
                    lines_to_remove |= line
                else:
                    seen_products[key] = line
            
            if lines_to_remove:
                # Gunakan unlink untuk menghapus baris duplikat dari database
                lines_to_remove.unlink()

    def write(self, vals):
        res = super().write(vals)
        # Jika ada perubahan pada order_line, jalankan fungsi penggabungan
        if 'order_line' in vals:
            self._merge_duplicate_lines()
        
        # Jika po_type atau warehouse_id diubah, update picking_type_id jika masih draft
        if ('po_type' in vals or 'warehouse_id' in vals) and all(order.state == 'draft' for order in self):

            for order in self:
                order._onchange_po_type_picking_type()
        return res

    @api.onchange('po_type')
    def _onchange_po_type_warn(self):
        """Peringatan jika tipe PO diubah saat sudah ada lines."""
        if self.order_line:
            return {
                'warning': {
                    'title': 'Perhatian!',
                    'message': 'Mengubah Type PO akan mempengaruhi filter produk pada baris PO dan Operation Type. '
                               'Pastikan produk yang dipilih sesuai dengan tipe PO baru.',
                }
            }


