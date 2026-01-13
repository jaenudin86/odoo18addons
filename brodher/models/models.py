# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class brodher(models.Model):
#     _name = 'brodher.brodher'
#     _description = 'brodher.brodher'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

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
            vals['default_code'] = self._generate_article_number(is_article)
                        # Jika PSIT, maka barcode = default_code
            if not is_article:     # is_article=False → PSIT
                vals['barcode'] = new_code
        return super(ProductTemplate, self).create(vals)
    def _generate_article_number(self, is_article):
        """Generate default_code:
        - ATC + DD + MM + YY + Seq(3) jika Is Article = True
        - PSIT + DD + MM + YY + Seq(3) jika Is Article = False
        """
        today = datetime.today()
        date_str = today.strftime('%d')
        month_str = today.strftime('%m')
        year_str = today.strftime('%y')

        prefix = 'ATC' if is_article else 'PSIT'
        seq_code = 'article.number.sequence' if is_article else 'pist.number.sequence'

        # Ambil nomor urut dari ir.sequence
        sequence = self.env['ir.sequence'].next_by_code(seq_code)
        if not sequence:
            sequence = '001'

        return f"{prefix}{date_str}{month_str}{year_str}{sequence}"

