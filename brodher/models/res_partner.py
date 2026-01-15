# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Field Tambahan sesuai Database Customer di gambar
    customer_ktp = fields.Char(string='Customer ID / KTP')
    date_of_birth = fields.Date(string='Date of Birth')
    # Field penampung code (Internal Reference Odoo biasanya menggunakan 'ref')
    
    @api.model
    def create(self, vals):
        """
        Generate Customer Code AC0000001 saat create
        """
        if not vals.get('ref'):
            # Memanggil sequence khusus customer
            seq_code = 'customer.code.sequence'
            # Kita gunakan prefix AC langsung di Python agar mudah dikontrol
            seq = self.env['ir.sequence'].next_by_code(seq_code) or '0000001'
            vals['ref'] = f"AC{seq}"
            
        return super(ResPartner, self).create(vals)