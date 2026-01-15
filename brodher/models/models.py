# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
import re

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

    def _generate_article_number(self, is_article):
        """
        - ATC: ATC + DD + MM + YY + XXX (12 Digit)
        - PSIT: PSIT + YY + XXXX (10 Digit)
        """
        now = datetime.today()
        ctx = dict(self._context, ir_sequence_date=now.strftime('%Y-%m-%d'))
        
        if is_article:
            prefix = 'ATC'
            date_str = now.strftime('%d%m%y')
            seq_code = 'article.number.sequence'
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code(seq_code) or '001'
            return f"{prefix}{date_str}{seq}"
        else:
            prefix = 'PSIT'
            year_str = now.strftime('%y')
            seq_code = 'pist.number.sequence'
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code(seq_code) or '0001'
            return f"{prefix}{year_str}{seq}"

    @api.model
    def create(self, vals):
        # Template tidak membuat barcode/default_code (hanya di variant)
        return super(ProductTemplate, self).create(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    static_barcode = fields.Char(string='Barcode Statis', store=True, readonly=True)

    # Sinkronisasi field dari template
    ingredients = fields.Text(related='product_tmpl_id.ingredients', store=True)
    brand = fields.Char(related='product_tmpl_id.brand', store=True)
    size = fields.Char(related='product_tmpl_id.size', store=True)
    is_article = fields.Boolean(related='product_tmpl_id.is_article', store=True)

    @api.model
    def create(self, vals):
        tmpl_id = vals.get('product_tmpl_id')
        if tmpl_id:
            tmpl = self.env['product.template'].browse(tmpl_id)
            
            # 1. Generate default_code & barcode Odoo
            if not vals.get('default_code'):
                code = tmpl._generate_article_number(tmpl.is_article)
                vals.update({
                    'default_code': code,
                    'barcode': code,
                })

            # 2. KHUSUS ATC: Generate Barcode Statis (xxMyyy)
            if tmpl.is_article:
                # xx: Ambil angka saja dari field size
                size_val = tmpl.size or ""
                xx = "".join(re.findall(r'\d+', size_val))
                
                # M: Konstanta ManasLu
                m_char = "M"
                
                # yyy: 1-3 huruf awal nama parfum
                # Menggunakan title case agar rapi (Contoh: Elanor -> Ela)
                name_clean = (tmpl.name or "")[:3].title()
                
                vals['static_barcode'] = f"{xx}{m_char}{name_clean}"
        
        return super(ProductProduct, self).create(vals)

    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        if 'default_code' in vals:
            for rec in self:
                if rec.default_code and rec.barcode != rec.default_code:
                    rec.barcode = rec.default_code
        return res

