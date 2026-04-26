# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        """
        Memastikan pencarian stok produk di POS dibatasi ke lokasi gudang POS tersebut.
        """
        params = super()._loader_params_product_product()
        # Di Odoo 18, kita bisa menyuntikkan context location ke loader
        params['context'].update({
            'location': self.config_id.picking_type_id.default_location_src_id.id,
            'warehouse': self.config_id.picking_type_id.warehouse_id.id,
        })
        return params

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Validasi akhir di sisi server saat order di-sinkron dari POS.
        Mengecek apakah Serial Number yang dijual benar-benar ada di gudang cabang tersebut.
        """
        orders = super().create(vals_list)
        for order in orders:
            pos_location = order.config_id.picking_type_id.default_location_src_id
            for line in order.lines:
                if line.pack_lot_ids:
                    for lot_line in line.pack_lot_ids:
                        # Cari Lot berdasarkan nama dan produk
                        lot = self.env['stock.lot'].search([
                            ('name', '=', lot_line.lot_name),
                            ('product_id', '=', line.product_id.id)
                        ], limit=1)
                        
                        if lot:
                            # Cek stok di lokasi POS (termasuk sub-lokasi)
                            quant = self.env['stock.quant'].search([
                                ('lot_id', '=', lot.id),
                                ('location_id', 'child_of', pos_location.id),
                                ('quantity', '>', 0)
                            ], limit=1)
                            
                            if not quant:
                                raise ValidationError(_(
                                    "Serial Number '%s' untuk produk '%s' tidak ditemukan di gudang %s. "
                                    "Mohon pastikan Anda men-scan barang yang ada di cabang ini."
                                ) % (lot.name, line.product_id.display_name, pos_location.complete_name))
        return orders
