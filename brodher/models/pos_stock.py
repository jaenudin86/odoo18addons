# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _register_hook(self):
        """
        Auto-update record rules of pos_warehouse_access in the database 
        to bypass Odoo's XML noupdate cache and prevent AccessErrors in POS.
        """
        res = super()._register_hook()
        
        # 1. Update rule stock_location
        rule_location = self.env.ref('pos_warehouse_access.stock_location_user_warehouse_rule', raise_if_not_found=False)
        if rule_location:
            rule_location.sudo().write({
                'domain_force': "['|', ('warehouse_id', '=', False), ('warehouse_id.user_access_ids', 'in', [user.id])]"
            })
            
        # 2. Update rule stock_quant
        rule_quant = self.env.ref('pos_warehouse_access.stock_quant_user_warehouse_rule', raise_if_not_found=False)
        if rule_quant:
            rule_quant.sudo().write({
                'domain_force': "['|', ('location_id.warehouse_id', '=', False), ('location_id.warehouse_id.user_access_ids', 'in', [user.id])]"
            })
            
        # 3. Update rule stock_picking
        rule_picking = self.env.ref('pos_warehouse_access.stock_picking_user_warehouse_rule', raise_if_not_found=False)
        if rule_picking:
            rule_picking.sudo().write({
                'domain_force': "['|', ('picking_type_id.warehouse_id', '=', False), ('picking_type_id.warehouse_id.user_access_ids', 'in', [user.id])]"
            })
            
        # 4. Update rule stock_picking_type
        rule_picking_type = self.env.ref('pos_warehouse_access.stock_picking_type_user_warehouse_rule', raise_if_not_found=False)
        if rule_picking_type:
            rule_picking_type.sudo().write({
                'domain_force': "['|', ('warehouse_id', '=', False), ('warehouse_id.user_access_ids', 'in', [user.id])]"
            })
            
        # 5. SELF-HEALING: Jasa/Diskon/Promo (Service) harus selalu memiliki tracking 'none'
        # Kadang di database produk promo bertipe 'service' ter-set tracking 'serial' secara tidak sengaja.
        try:
            wrong_service_products = self.env['product.product'].sudo().search([
                ('type', '=', 'service'),
                ('tracking', '!=', 'none')
            ])
            if wrong_service_products:
                wrong_service_products.write({'tracking': 'none'})
                
            wrong_service_templates = self.env['product.template'].sudo().search([
                ('type', '=', 'service'),
                ('tracking', '!=', 'none')
            ])
            if wrong_service_templates:
                wrong_service_templates.write({'tracking': 'none'})
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
