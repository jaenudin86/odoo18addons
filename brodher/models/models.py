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
    
    def create_variant_ids(self):
        """Override untuk set default_code dan barcode pada variant yang baru dibuat"""
        result = super(ProductTemplate, self).create_variant_ids()
        
        for template in self:
            for variant in template.product_variant_ids:
                # Jika variant belum punya default_code, generate
                if not variant.default_code:
                    variant_code = self._generate_variant_code(template, variant)
                    variant.default_code = variant_code
                    variant.barcode = variant_code
                    
        return result
    
    def _generate_variant_code(self, template, variant):
        """Generate kode untuk variant berdasarkan attribute"""
        base_code = template.default_code or self._generate_article_number(template.is_article)
        
        # Ambil nilai attribute untuk variant
        variant_suffix = ""
        for value in variant.product_template_attribute_value_ids:
            # Ambil 2-3 karakter pertama dari attribute value
            attr_code = value.name[:3].upper().replace(" ", "")
            variant_suffix += attr_code
            
        if variant_suffix:
            return f"{base_code}-{variant_suffix}"
        else:
            return base_code


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    @api.model
    def create(self, vals):
        """Override create untuk set barcode = default_code"""
        result = super(ProductProduct, self).create(vals)
        
        # Set barcode sama dengan default_code
        if result.default_code and not result.barcode:
            result.barcode = result.default_code
            
        return result
    
    def write(self, vals):
        """Override write untuk sync barcode dengan default_code"""
        result = super(ProductProduct, self).write(vals)
        
        # Jika default_code diubah, update barcode juga
        if 'default_code' in vals:
            for record in self:
                if record.default_code:
                    record.barcode = record.default_code
                    
        return result