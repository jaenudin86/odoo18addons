# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
import re


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # =========================
    # FIELD TAMBAHAN
    # =========================

# psit
    brand = fields.Char(string="Brand")
    dimension = fields.Char(string="Dimension")
    base_colour = fields.Char(string='Base Colour')
    text_colour = fields.Char(string='Text Colour')
    size = fields.Char(string="Size")

# atc
    ingredients = fields.Text(string="Ingredients")
    Edition = fields.Char(string="Edition")     
    gross_weight = fields.Float(string='Gross Weight')
    net_weight = fields.Float(string='Net Weight')
    net_net_weight = fields.Float(string='Net Net Weight')
    date_month_year = fields.Date(string='Date (Month/Year) Design')

    is_article = fields.Selection(
        [('yes', 'ATC'), ('no', 'PSIT')],
        string="Is Article",
        default='no'
    )

    # =========================
    # GENERATE ARTICLE NUMBER
    # =========================
    def _generate_article_number(self, is_article):
        """
        - ATC  : ATC + DDMMYY + XXX (3 digit)
        - PSIT : PSIT + YY + XXXX (4 digit)
        """
        now = datetime.today()
        ctx = dict(self._context, ir_sequence_date=now.strftime('%Y-%m-%d'))

        if is_article == 'yes':
            prefix = 'ATC'
            date_str = now.strftime('%d%m%y')
            seq = self.env['ir.sequence'].with_context(ctx)\
                .next_by_code('article.number.sequence') or '001'
            # Pastikan 3 digit
            seq = str(seq).zfill(3)
            return f"{prefix}{date_str}{seq}"
        else:
            prefix = 'PSIT'
            year_str = now.strftime('%y')
            seq = self.env['ir.sequence'].with_context(ctx)\
                .next_by_code('pist.number.sequence') or '0001'
            # Pastikan 4 digit
            seq = str(seq).zfill(4)
            return f"{prefix}{year_str}{seq}"

    @api.model
    def create(self, vals):
        # Selalu stockable
        vals.setdefault('is_storable', True)
        vals.setdefault('type', 'product')

        # AUTO TRACK INVENTORY berdasarkan is_article
        if vals.get('is_article') == 'yes':
            vals.update({
                'tracking': 'serial',   # ATC → by serial number
            })
        else:
            vals.update({
                'tracking': 'none',     # PSIT → by quantity
            })

        # Generate default_code di level template jika belum ada
        if not vals.get('default_code'):
            is_article = vals.get('is_article', 'no')
            vals['default_code'] = self._generate_article_number(is_article)

        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)

        # Update tracking jika is_article berubah
        if 'is_article' in vals:
            for rec in self:
                if rec.is_article == 'yes':
                    rec.tracking = 'serial'
                else:
                    rec.tracking = 'none'

        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    static_barcode = fields.Char(
        string='Barcode Statis',
        readonly=True,
        store=True
    )

    # =========================
    # RELATED FIELD
    # =========================
    brand = fields.Char(related='product_tmpl_id.brand', store=True)
    dimension = fields.Char(related='product_tmpl_id.dimension', store=True)
    base_colour = fields.Char(related='product_tmpl_id.base_colour', store=True)
    text_colour = fields.Char(related='product_tmpl_id.text_colour', store=True)
    size = fields.Char(related='product_tmpl_id.size', store=True)

    ingredients = fields.Text(related='product_tmpl_id.ingredients', store=True)
    Edition = fields.Char(related='product_tmpl_id.Edition', store=True)
    gross_weight = fields.Float(related='product_tmpl_id.gross_weight', store=True)
    net_weight = fields.Float(related='product_tmpl_id.net_weight', store=True)
    net_net_weight = fields.Float(related='product_tmpl_id.net_net_weight', store=True)
    is_article = fields.Selection(related='product_tmpl_id.is_article', store=True)
    date_month_year = fields.Date(related='product_tmpl_id.date_month_year', store=True)

    @api.model
    def create(self, vals):
        tmpl_id = vals.get('product_tmpl_id')
        
        if tmpl_id:
            tmpl = self.env['product.template'].browse(tmpl_id)
            
            # Untuk variant, gunakan default_code dari template sebagai base
            # lalu tambahkan suffix jika ada variant attributes
            if not vals.get('default_code'):
                base_code = tmpl.default_code
                
                # Jika produk punya variant attributes, tambahkan suffix
                if vals.get('product_template_attribute_value_ids'):
                    # Generate unique suffix untuk variant
                    variant_count = self.search_count([('product_tmpl_id', '=', tmpl_id)])
                    variant_suffix = f"-V{variant_count + 1:02d}"
                    code = f"{base_code}{variant_suffix}"
                else:
                    # Produk tunggal tanpa variant
                    code = base_code
                
                vals.update({
                    'default_code': code,
                    'barcode': code,
                })
            # Jika default_code sudah diisi manual, set barcode sama dengan default_code
            elif not vals.get('barcode'):
                vals['barcode'] = vals.get('default_code')

        return super().create(vals)