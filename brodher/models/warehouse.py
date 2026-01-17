# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    # ========================================
    # WAREHOUSE TYPE & NUMBERING
    # ========================================
    
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
    
    # ========================================
    # CONTACT INFORMATION
    # ========================================
    
    x_pic_name = fields.Char(string='PIC Name')
    x_email_warehouse = fields.Char(string='Email Warehouse')
    x_npwp_warehouse = fields.Char(string='NPWP Warehouse')
    x_mobile_phone_no = fields.Char(string='Mobile Phone No')
    
    # ========================================
    # ADDRESS INFORMATION
    # ========================================
    
    x_legal_address = fields.Text(string='Legal Address')
    x_operational_address = fields.Text(string='Operational Address')
    x_location_address = fields.Text(string='Location Address')
    x_city_name = fields.Char(string='City Name')
    x_zip_code = fields.Char(string='Zip Code')
    
    # ========================================
    # STORE INFORMATION
    # ========================================
    
    x_pic_store = fields.Char(string='PIC Store')
    x_location = fields.Char(string='Location')
    x_dept_store_name = fields.Char(string='Dept Store Name')
    x_location_name = fields.Char(string='Location Name')
    x_receipt_store = fields.Char(string='Receipt Store')
    
    # ========================================
    # PHOTOS
    # ========================================
    
    x_front_photo = fields.Binary(string='Front Photo')
    x_inside_photo = fields.Binary(string='Inside Photo')
    x_photo_spv_spl = fields.Binary(string='Photo SPV and SPL')
    x_qr_code = fields.Binary(string='QR Code')
    
    # ========================================
    # AUTO-NUMBERING
    # ========================================
    
    @api.model
    def create(self, vals):
        """Auto-generate warehouse number saat create"""
        if vals.get('x_warehouse_type') and vals.get('x_brand'):
            vals['x_warehouse_number'] = self._generate_warehouse_number(
                vals['x_warehouse_type'],
                vals['x_brand']
            )
        return super(StockWarehouse, self).create(vals)
    
    def _generate_warehouse_number(self, warehouse_type, brand):
        """
        Generate warehouse number:
        - WHC: WHCMNL001
        - WHO: WHOMNL002
        - WHS: WHSMNL003, WHSMNL004, dst
        """
        brand = brand.upper()[:3]  # Ambil 3 karakter pertama, uppercase
        
        # Tentukan prefix
        if warehouse_type == 'whc':
            prefix = 'WHC'
            start_num = 1
        elif warehouse_type == 'who':
            prefix = 'WHO'
            start_num = 2
        else:  # whs
            prefix = 'WHS'
            start_num = 3
        
        # Cari nomor terakhir
        last_warehouse = self.search([
            ('x_warehouse_type', '=', warehouse_type),
            ('x_brand', '=', brand),
            ('x_warehouse_number', '!=', False)
        ], order='x_warehouse_number desc', limit=1)
        
        if last_warehouse and last_warehouse.x_warehouse_number:
            # Ambil 3 digit terakhir dan increment
            last_num = int(last_warehouse.x_warehouse_number[-3:])
            next_num = last_num + 1
        else:
            next_num = start_num
        
        # Format: WHCMNL001
        return f"{prefix}{brand}{str(next_num).zfill(3)}"