# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    ingredients = fields.Text(string="Ingredients")
    brand = fields.Char(string="Brand")
    size = fields.Char(string="Size")
    is_article = fields.Boolean(string='Is Article', default=False)
    gross_weight = fields.Float(string='Gross Weight')
    net_weight = fields.Float(string='Net Weight')
    net_net_weight = fields.Float(string='Net Net Weight')
    base_colour = fields.Char(string='Base Colour')
    text_colour = fields.Char(string='Text Colour')
    
    @api.model
    def create(self, vals):
        # Jika default_code kosong, generate otomatis
        if not vals.get('default_code'):
            is_article = vals.get('is_article', False)
            new_code = self._generate_article_number(is_article)
            vals['default_code'] = new_code
            
            # Jika PSIT, maka barcode = default_code
            if not is_article:  # is_article=False → PSIT
                vals['barcode'] = new_code
                
        return super(ProductTemplate, self).create(vals)
    
    def write(self, vals):
        """Override write untuk update barcode saat default_code berubah"""
        result = super(ProductTemplate, self).write(vals)
        
        # Jika default_code diubah dan is_article=False, update barcode
        if 'default_code' in vals:
            for record in self:
                if not record.is_article and record.default_code:
                    record.barcode = record.default_code
                    
                # Update barcode untuk semua variant
                for variant in record.product_variant_ids:
                    if variant.default_code:
                        variant.barcode = variant.default_code
                        
        return result
    
    def _generate_article_number(self, is_article):
        """Generate default_code:
        - ATC + YY + Seq(3) jika Is Article = True
        - PSIT + YY + Seq(3) jika Is Article = False
        """
        today = datetime.today()
        year_str = today.strftime('%y')
        
        prefix = 'ATC' if is_article else 'PSIT'
        seq_code = 'article.number.sequence' if is_article else 'pist.number.sequence'
        
        # Ambil nomor urut dari ir.sequence
        sequence = self.env['ir.sequence'].next_by_code(seq_code)
        if not sequence:
            sequence = '001'
            
        return f"{prefix}{year_str}{sequence}"
    
    def _create_variant_ids(self):
        """Override untuk set default_code dan barcode pada variant yang baru dibuat"""
        result = super(ProductTemplate, self)._create_variant_ids()
        
        for template in self:
            for variant in template.product_variant_ids:
                # Jika variant belum punya default_code atau masih sama dengan template
                if not variant.default_code or variant.default_code == template.default_code:
                    # Generate sequence baru untuk variant ini
                    variant_code = self._generate_article_number(template.is_article)
                    variant.write({
                        'default_code': variant_code,
                        'barcode': variant_code
                    })
                elif variant.default_code and not variant.barcode:
                    # Jika sudah ada default_code tapi belum ada barcode
                    variant.barcode = variant.default_code
                    
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Inherit fields dari template agar bisa diakses di variant
    ingredients = fields.Text(related='product_tmpl_id.ingredients', string="Ingredients", readonly=False, store=True)
    brand = fields.Char(related='product_tmpl_id.brand', string="Brand", readonly=False, store=True)
    size = fields.Char(related='product_tmpl_id.size', string="Size", readonly=False, store=True)
    is_article = fields.Boolean(related='product_tmpl_id.is_article', string='Is Article', readonly=False, store=True)
    gross_weight = fields.Float(related='product_tmpl_id.gross_weight', string='Gross Weight', readonly=False, store=True)
    net_weight = fields.Float(related='product_tmpl_id.net_weight', string='Net Weight', readonly=False, store=True)
    net_net_weight = fields.Float(related='product_tmpl_id.net_net_weight', string='Net Net Weight', readonly=False, store=True)
    base_colour = fields.Char(related='product_tmpl_id.base_colour', string='Base Colour', readonly=False, store=True)
    text_colour = fields.Char(related='product_tmpl_id.text_colour', string='Text Colour', readonly=False, store=True)
    
    @api.model
    def create(self, vals):
        """Override create untuk set default_code dan barcode"""
        # Jika belum ada default_code, generate dari sequence
        if not vals.get('default_code'):
            # Cek is_article dari template atau vals
            is_article = False
            if 'product_tmpl_id' in vals:
                template = self.env['product.template'].browse(vals['product_tmpl_id'])
                is_article = template.is_article
            elif 'is_article' in vals:
                is_article = vals['is_article']
                
            # Generate code baru
            new_code = self.env['product.template']._generate_article_number(is_article)
            vals['default_code'] = new_code
            vals['barcode'] = new_code
            
        result = super(ProductProduct, self).create(vals)
        
        # Set barcode sama dengan default_code jika belum ada
        if result.default_code and not result.barcode:
            result.barcode = result.default_code
            
        return result
    
    def write(self, vals):
        """Override write untuk sync barcode dengan default_code"""
        result = super(ProductProduct, self).write(vals)
        
        # Jika default_code diubah, update barcode juga
        if 'default_code' in vals:
            for record in self:
                if record.default_code and record.default_code != record.barcode:
                    record.barcode = record.default_code
                    
        return result