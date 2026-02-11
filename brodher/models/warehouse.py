# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    # ========================================
    # WAREHOUSE TYPE & NUMBERING
    # ========================================
    # Redefine code agar sinkron dengan auto-number
    code = fields.Char('Short Name', size=20, required=True, help="Short name for this warehouse.")
    
    x_warehouse_type = fields.Selection([
        ('whc', 'WHC - Gudang Pusat'),
        ('who', 'WHO - Gudang Online'),
        ('whs', 'WHS - Gudang Offline')
    ], string='Warehouse Type', required=True)
    
    x_warehouse_number = fields.Char(
        string='Warehouse Number',
        readonly=True,
        copy=False,
        help='Auto-generated: WHCMNL001, WHOMNL002, WHSMNL003'
    )
    
    x_brand = fields.Char(
        string='Brand',
        required=True,
        help='Brand code 3 karakter (contoh: MNL)'
    )
    
    # ... (Field PIC, Address, Store, Photos tetap sama seperti kode Anda sebelumnya) ...
    x_pic_name = fields.Char(string='PIC Name')
    x_email_warehouse = fields.Char(string='Email Warehouse')
    x_npwp_warehouse = fields.Char(string='NPWP Warehouse')
    x_mobile_phone_no = fields.Char(string='Mobile Phone No')
    x_legal_address = fields.Text(string='Legal Address')
    x_operational_address = fields.Text(string='Operational Address')
    x_location_address = fields.Text(string='Location Address')
    x_city_name = fields.Char(string='City Name')
    x_zip_code = fields.Char(string='Zip Code')
    x_pic_store = fields.Char(string='PIC Store')
    x_location = fields.Char(string='Location')
    x_dept_store_name = fields.Char(string='Dept Store Name')
    x_location_name = fields.Char(string='Location Name')
    x_receipt_store = fields.Char(string='Receipt Store')
    x_front_photo = fields.Binary(string='Front Photo')
    x_inside_photo = fields.Binary(string='Inside Photo')
    x_photo_spv_spl = fields.Binary(string='Photo SPV and SPL')
    x_qr_code = fields.Binary(string='QR Code')

    # ========================================
    # LOGIC AUTO-NUMBERING
    # ========================================
    
    @api.model
    def create(self, vals):
        """Generate nomor saat record dibuat"""
        if vals.get('x_warehouse_type') and vals.get('x_brand'):
            generated_number = self._generate_warehouse_number(
                vals['x_warehouse_type'], 
                vals['x_brand']
            )
            vals['x_warehouse_number'] = generated_number
            vals['code'] = generated_number
            
        return super(StockWarehouse, self).create(vals)

    def write(self, vals):
        """Update nomor jika Brand atau Tipe berubah"""
        res = super(StockWarehouse, self).write(vals)
        
        # Jika brand atau type diubah, generate ulang kodenya
        if 'x_brand' in vals or 'x_warehouse_type' in vals:
            for rec in self:
                new_number = rec._generate_warehouse_number(rec.x_warehouse_type, rec.x_brand)
                # Gunakan super write agar tidak trigger loop infinite
                super(StockWarehouse, rec).write({
                    'x_warehouse_number': new_number,
                    'code': new_number
                })
        return res

    def _generate_warehouse_number(self, warehouse_type, brand):
        """
        Logika mencari nomor urut terakhir berdasarkan Prefix + Brand
        """
        brand_code = (brand or '').upper()[:3]
        if not brand_code:
            brand_code = 'XXX'
            
        # Mapping Prefix & Start Number
        prefix_map = {'whc': ('WHC', 1), 'who': ('WHO', 2), 'whs': ('WHS', 3)}
        prefix, start_num = prefix_map.get(warehouse_type, ('WHS', 3))
        
        # Cari nomor terakhir di database yang punya prefix & brand yang sama
        # Mencari di field 'code' karena field ini yang punya constraint UNIQUE di Odoo
        search_pattern = f"{prefix}{brand_code}%"
        last_rec = self.env['stock.warehouse'].search([
            ('code', '=like', search_pattern)
        ], order='code desc', limit=1)
        
        if last_rec:
            # Mengambil 3 digit terakhir dari string (contoh: WHCMNL005 -> 005)
            try:
                last_num_str = last_rec.code[-3:]
                next_num = int(last_num_str) + 1
            except (ValueError, TypeError):
                next_num = start_num
        else:
            next_num = start_num
            
        generated = f"{prefix}{brand_code}{str(next_num).zfill(3)}"
        
        # Safety Check: Pastikan hasil generate benar-benar belum ada di database
        # (Jika ada lubang/data manual, dia akan naik terus sampai ketemu yang kosong)
        while self.env['stock.warehouse'].search_count([('code', '=', generated)]) > 0:
            next_num += 1
            generated = f"{prefix}{brand_code}{str(next_num).zfill(3)}"
            
        return generated