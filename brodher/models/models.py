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

    # ==============================
    # TEMPLATE CREATE
    # ==============================
    @api.model
    def create(self, vals):
        """
        - Article = TRUE  → template auto-generate default_code + barcode
        - Article = FALSE → template TIDAK generate apa pun
        """
        if vals.get('is_article') and not vals.get('default_code'):
            code = self._generate_article_number(True)
            vals.update({
                'default_code': code,
                'barcode': code,
            })

        return super().create(vals)

    # ==============================
    # VARIANT CREATE
    # ==============================
    def _create_variant_ids(self):
        """
        Semua VARIANT auto-generate default_code & barcode
        """
        res = super()._create_variant_ids()

        for template in self:
            for variant in template.product_variant_ids:
                if not variant.default_code:
                    code = self._generate_article_number(template.is_article)
                    variant.write({
                        'default_code': code,
                        'barcode': code,
                    })
                elif not variant.barcode:
                    variant.barcode = variant.default_code

        return res

    # ==============================
    # SEQUENCE GENERATOR
    # ==============================
    def _generate_article_number(self, is_article):
        """
        ATCYYXXX → Article
        PSITYYXXX → Non Article
        """
        year = datetime.today().strftime('%y')
        prefix = 'ATC' if is_article else 'PSIT'
        seq_code = 'article.number.sequence' if is_article else 'psit.number.sequence'

        seq = self.env['ir.sequence'].next_by_code(seq_code) or '001'
        return f"{prefix}{year}{seq}"
class ProductProduct(models.Model):
    _inherit = 'product.product'

    ingredients = fields.Text(related='product_tmpl_id.ingredients', store=True)
    brand = fields.Char(related='product_tmpl_id.brand', store=True)
    size = fields.Char(related='product_tmpl_id.size', store=True)
    is_article = fields.Boolean(related='product_tmpl_id.is_article', store=True)

    gross_weight = fields.Float(related='product_tmpl_id.gross_weight', store=True)
    net_weight = fields.Float(related='product_tmpl_id.net_weight', store=True)
    net_net_weight = fields.Float(related='product_tmpl_id.net_net_weight', store=True)
    base_colour = fields.Char(related='product_tmpl_id.base_colour', store=True)
    text_colour = fields.Char(related='product_tmpl_id.text_colour', store=True)

    @api.model
    def create(self, vals):
        """
        Jika variant dibuat MANUAL (bukan dari template)
        """
        if not vals.get('default_code'):
            tmpl = self.env['product.template'].browse(vals.get('product_tmpl_id'))
            code = tmpl._generate_article_number(tmpl.is_article)
            vals.update({
                'default_code': code,
                'barcode': code,
            })

        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        if 'default_code' in vals:
            for rec in self:
                if rec.default_code and rec.barcode != rec.default_code:
                    rec.barcode = rec.default_code
        return res
