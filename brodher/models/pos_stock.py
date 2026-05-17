# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosSession(models.Model):
    _inherit = 'pos.session'

    def init(self):
        super().init()
        # Safe SQL update to bypass Odoo registry locks and force-apply rules during module upgrade
        self.env.cr.execute("""
            -- 0. REPAIR: Perbaiki jika ada record rule yang terlanjur corrupt berisi string 'false' atau 'False' di database
            UPDATE ir_rule 
            SET domain_force = '[]' 
            WHERE domain_force = 'false' OR domain_force = 'False';

            -- 1. stock_location rule (domain_force = [(1, '=', 1)] to allow reading all locations)
            UPDATE ir_rule 
            SET domain_force = '[(1, '=', 1)]',
                perm_read = true
            WHERE id = (
                SELECT res_id FROM ir_model_data 
                WHERE name = 'stock_location_user_warehouse_rule' AND module = 'pos_warehouse_access'
            );
            
            -- 2. stock_quant rule
            UPDATE ir_rule 
            SET domain_force = $$['|', ('location_id.warehouse_id', '=', False), ('location_id.warehouse_id.user_access_ids', 'in', [user.id])]$$
            WHERE id = (
                SELECT res_id FROM ir_model_data 
                WHERE name = 'stock_quant_user_warehouse_rule' AND module = 'pos_warehouse_access'
            );
            
            -- 3. stock_picking rule
            UPDATE ir_rule 
            SET domain_force = $$['|', ('picking_type_id.warehouse_id', '=', False), ('picking_type_id.warehouse_id.user_access_ids', 'in', [user.id])]$$
            WHERE id = (
                SELECT res_id FROM ir_model_data 
                WHERE name = 'stock_picking_user_warehouse_rule' AND module = 'pos_warehouse_access'
            );
            
            -- 4. stock_picking_type rule
            UPDATE ir_rule 
            SET domain_force = $$['|', ('warehouse_id', '=', False), ('warehouse_id.user_access_ids', 'in', [user.id])]$$
            WHERE id = (
                SELECT res_id FROM ir_model_data 
                WHERE name = 'stock_picking_type_user_warehouse_rule' AND module = 'pos_warehouse_access'
            );
        """)

    @api.model
    def _register_hook(self):
        """
        Auto-update products for discount/promo self-healing.
        This is safe because it only modifies product.product/template records.
        """
        res = super()._register_hook()
        
        # SELF-HEALING: Jasa/Diskon/Promo harus selalu bersih dari IR Number & Tracking
        # Menghapus default_code (IR Number) yang sempat ter-generate oleh bug lama,
        # dan mereset tracking ke 'none' serta is_article ke 'other' tanpa mengubah tipe produk (goods).
        try:
            domain = [
                '|', '|', '|',
                ('type', '=', 'service'),
                ('name', 'ilike', 'disc'),
                ('name', 'ilike', 'discount'),
                ('name', 'ilike', 'promo')
            ]
            
            wrong_service_products = self.env['product.product'].sudo().search(domain)
            if wrong_service_products:
                wrong_service_products.write({
                    'tracking': 'none',
                    'is_article': 'other',
                    'default_code': False
                })
                
            wrong_service_templates = self.env['product.template'].sudo().search(domain)
            if wrong_service_templates:
                wrong_service_templates.write({
                    'tracking': 'none',
                    'is_article': 'other',
                    'default_code': False
                })
        except Exception as e:
            pass
            
        return res

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
                # Coba pencarian toleran ilike jika pencarian persis gagal
                product = self.env['product.product'].search([
                    '|', ('name', 'ilike', product_name), ('display_name', 'ilike', product_name)
                ], limit=1)
            
        if not product:
            return {'status': 'error', 'message': f"Produk '{product_name}' tidak ditemukan."}
            
        # 1. Cari Lot berdasarkan nama dan produk
        lot = self.env['stock.lot'].sudo().search([
            ('name', '=', lot_name),
            ('product_id', '=', product.id)
        ], limit=1)
        
        # Pengecekan silang jika lot terdaftar di produk lain
        if not lot:
            other_lot = self.env['stock.lot'].sudo().search([('name', '=', lot_name)], limit=1)
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
        quant_domain = [
            ('lot_id', '=', lot.id),
            ('location_id', 'child_of', pos_location.id),
            ('quantity', '>', 0)
        ]
        
        # Integrasi pos_warehouse_access: jika user dibatasi gudangnya, perketat pencarian
        if 'warehouse_access_ids' in self.env.user._fields:
            allowed_warehouses = self.env.user.warehouse_access_ids
            if allowed_warehouses:
                quant_domain.append(('location_id.warehouse_id', 'in', allowed_warehouses.ids))
                
        quant = self.env['stock.quant'].sudo().search(quant_domain, limit=1)
        
        if not quant:
            allowed_msg = ""
            if 'warehouse_access_ids' in self.env.user._fields and self.env.user.warehouse_access_ids:
                allowed_names = ", ".join(self.env.user.warehouse_access_ids.mapped('name'))
                allowed_msg = f" di gudang akses Anda ({allowed_names})"
            return {
                'status': 'no_stock',
                'message': f"Serial Number '{lot_name}' ditemukan, tapi TIDAK ADA STOK{allowed_msg} di bawah lokasi POS {pos_location.complete_name}."
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
                        # Cari Lot berdasarkan nama dan produk dengan privileges tinggi
                        lot = self.env['stock.lot'].sudo().search([
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
                            
                            # Cek stok di lokasi POS (termasuk sub-lokasi) dengan privileges tinggi
                            quant_domain = [
                                ('lot_id', '=', lot.id),
                                ('location_id', 'child_of', pos_location.id),
                                ('quantity', '>', 0)
                            ]
                            
                            # Integrasi pos_warehouse_access: jika user dibatasi gudangnya
                            if 'warehouse_access_ids' in self.env.user._fields:
                                allowed_warehouses = self.env.user.warehouse_access_ids
                                if allowed_warehouses:
                                    quant_domain.append(('location_id.warehouse_id', 'in', allowed_warehouses.ids))
                                    
                            quant = self.env['stock.quant'].sudo().search(quant_domain, limit=1)
                            
                            if not quant:
                                raise ValidationError(_(
                                    "Serial Number '%s' ditemukan, tapi tidak ada di gudang POS %s."
                                ) % (lot.name, pos_location.complete_name))
        return orders
