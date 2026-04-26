# -*- coding: utf-8 -*-
from odoo import api, fields, models

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    operation_category = fields.Selection([
        ('atc', 'ATC (Makloon)'),
        ('psit', 'PSIT'),
        ('other', 'Other / General'),
    ], string='Operation Category', default='other', help="Kategori operasi untuk memisahkan barang ATC dan PSIT")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    operation_category = fields.Selection(related='picking_type_id.operation_category', store=True)

    @api.constrains('move_ids', 'picking_type_id')
    def _check_product_category_match(self):
        """Pastikan produk dalam picking sesuai dengan kategori operasi."""
        for picking in self:
            if not picking.picking_type_id or picking.picking_type_id.operation_category == 'other':
                continue
            
            category = picking.picking_type_id.operation_category
            article_map = {'atc': 'yes', 'psit': 'no'}
            required_article_type = article_map.get(category)

            for move in picking.move_ids:
                if move.product_id.is_article != required_article_type:
                    type_label = 'ATC' if required_article_type == 'yes' else 'PSIT'
                    raise ValidationError(
                        f'Operasi ini khusus untuk barang {type_label}! '
                        f'Produk "{move.product_id.display_name}" tidak cocok dengan kategori ini.'
                    )

