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

    @api.model
    def check_lot_validation(self, product_id, lot_name, product_name=""):
        """
        Mengecek apakah serial number / lot untuk produk tertentu 
        terdaftar dan tersedia di lokasi POS session yang sedang aktif.
        """
        # Cari session yang sedang aktif untuk user saat ini
        session = self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('user_id', '=', self.env.user.id)
        ], limit=1)
        
        if not session:
            # Fallback jika tidak ada session spesifik untuk user
            session = self.env['pos.session'].search([('state', '=', 'opened')], limit=1)
            
        if not session:
            return {'status': 'error', 'message': 'Tidak ada POS Session yang aktif.'}
            
        config = session.config_id
        pos_location = config.picking_type_id.default_location_src_id
        
        # Fallback pencarian produk berdasarkan product_id atau product_name
        product = None
        if product_id:
            product = self.env['product.product'].browse(product_id)
        if (not product or not product.exists()) and product_name:
            product = self.env['product.product'].search([
                '|', ('name', '=', product_name), ('display_name', '=', product_name)
            ], limit=1)
            
        if not product:
            return {'status': 'error', 'message': f"Produk '{product_name}' tidak ditemukan."}
            
        # 1. Cari Lot berdasarkan nama dan produk
        lot = self.env['stock.lot'].search([
            ('name', '=', lot_name),
            ('product_id', '=', product.id)
        ], limit=1)
        
        # Pengecekan silang jika lot terdaftar di produk lain
        if not lot:
            other_lot = self.env['stock.lot'].search([('name', '=', lot_name)], limit=1)
            if other_lot:
                return {
                    'status': 'invalid',
                    'message': f"Serial Number '{lot_name}' terdaftar untuk produk '{other_lot.product_id.display_name}', bukan untuk '{product.display_name}'!"
                }
            return {
                'status': 'invalid', 
                'message': f"Serial Number '{lot_name}' TIDAK TERDAFTAR untuk produk '{product.display_name}'. Mohon gunakan QR Code yang valid."
            }
            
        # 2. Cek stok di lokasi POS (termasuk sub-lokasi)
        quant = self.env['stock.quant'].search([
            ('lot_id', '=', lot.id),
            ('location_id', 'child_of', pos_location.id),
            ('quantity', '>', 0)
        ], limit=1)
        
        if not quant:
            return {
                'status': 'no_stock',
                'message': f"Serial Number '{lot_name}' ditemukan, tapi TIDAK ADA DI GUDANG {pos_location.complete_name}. Pastikan barang tersebut sudah dimutasi ke cabang ini."
            }
            
        return {'status': 'ok'}

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
                        
                        # PERKETAT: Jika produk adalah SN atau Lot, maka Lot WAJIB valid dan ada di lokasi POS
                        if line.product_id.tracking in ('serial', 'lot'):
                            if not lot:
                                raise ValidationError(_(
                                    "Serial Number '%s' tidak terdaftar untuk produk '%s'. "
                                    "Mohon scan QR Code yang valid."
                                ) % (lot_line.lot_name, line.product_id.display_name))
                            
                            # Cek stok di lokasi POS (termasuk sub-lokasi)
                            quant = self.env['stock.quant'].search([
                                ('lot_id', '=', lot.id),
                                ('location_id', 'child_of', pos_location.id),
                                ('quantity', '>', 0)
                            ], limit=1)
                            
                            if not quant:
                                raise ValidationError(_(
                                    "Serial Number '%s' ditemukan, tapi tidak ada di gudang %s. "
                                    "Pastikan barang tersebut sudah dimutasi ke cabang ini."
                                ) % (lot.name, pos_location.complete_name))
        return orders
