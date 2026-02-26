# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # =========================
    # FIELD TAMBAHAN
    # =========================
    parent_article_id = fields.Many2one(
        'product.template',
        string="Parent ATC",
        domain=[('is_article', '=', 'yes')]
    )

    brand = fields.Char(string="Brand*")
    dimension = fields.Char(string="Dimension*")
    base_colour = fields.Char(string='Base Colour')
    text_colour = fields.Char(string='Text Colour')
    size = fields.Char(string="Size*")

    ingredients = fields.Text(string="Ingredients*")
    Edition = fields.Char(string="Edition*")
    gross_weight = fields.Float(string='Gross Weight*')
    net_weight = fields.Float(string='Net Weight*')
    net_net_weight = fields.Float(string='Net Net Weight*')
    date_month_year = fields.Date(string='Date (Month/Year) Design*')

    is_article = fields.Selection(
        [('yes', 'ATC'), ('no', 'PSIT')],
        string="Is Article",
        default='no'
    )

    # =========================
    # ONCHANGE METHODS
    # =========================
    @api.onchange('is_article')
    def _onchange_is_article(self):
        """Reset default_code ketika is_article berubah"""
        if self.is_article in ['yes', 'no']:
            self.default_code = ''

    @api.onchange('parent_article_id')
    def _onchange_parent_article(self):
        if self.is_article == 'var' and self.parent_article_id:
            self.default_code = self.parent_article_id.default_code

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
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code('article.number.sequence') or '001'
            seq = str(seq).zfill(3)
            return f"{prefix}{date_str}{seq}"
        else:
            prefix = 'PSIT'
            year_str = now.strftime('%y')
            # FIX: typo diperbaiki dari 'pist.number.sequence' → 'psit.number.sequence'
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code('psit.number.sequence') or '0001'
            seq = str(seq).zfill(4)
            return f"{prefix}{year_str}{seq}"

    # =========================
    # CREATE
    # =========================
    @api.model
    def create(self, vals):
        vals.setdefault('is_storable', True)
        vals.setdefault('type', 'product')

        is_article = vals.get('is_article', 'no')

        # AUTO TRACK INVENTORY
        if is_article == 'yes':
            vals['tracking'] = 'serial'
        else:
            vals['tracking'] = 'none'

        # ================================================================
        # ATC  → generate nomor di TEMPLATE, nanti di-sync ke variant
        # PSIT → TIDAK generate nomor di template,
        #         nomor di-generate nanti per variant di ProductProduct.create
        # ================================================================
        if is_article == 'yes':
            default_code = vals.get('default_code')
            if not default_code or (isinstance(default_code, str) and not default_code.strip()):
                vals['default_code'] = self._generate_article_number('yes')
        else:
            # PSIT: kosongkan default_code di template
            vals['default_code'] = False

        template = super(ProductTemplate, self).create(vals)

        # ================================================================
        # PENTING: Setelah template ATC dibuat, Odoo otomatis membuat
        # variant pertama. Kita harus sync default_code ke variant tsb.
        # ================================================================
        if is_article == 'yes' and template.default_code:
            template.product_variant_ids.write({
                'default_code': template.default_code
            })

        return template

    # =========================
    # WRITE
    # =========================
    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)

        for rec in self:
            # Jika is_article berubah → update tracking semua variant
            if 'is_article' in vals:
                new_tracking = 'serial' if rec.is_article == 'yes' else 'none'
                rec.product_variant_ids.write({'tracking': new_tracking})

            # Jika default_code template ATC berubah → sync ke semua variant
            if 'default_code' in vals and rec.is_article == 'yes':
                rec.product_variant_ids.write({'default_code': vals['default_code']})

        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    static_barcode = fields.Char(string='Barcode Statis', readonly=True)

    # =========================
    # RELATED FIELDS
    # =========================
    brand = fields.Char(related='product_tmpl_id.brand', store=True)
    base_colour = fields.Char(related='product_tmpl_id.base_colour', store=True)
    text_colour = fields.Char(related='product_tmpl_id.text_colour', store=True)
    size = fields.Char(related='product_tmpl_id.size', store=True)
    ingredients = fields.Text(related='product_tmpl_id.ingredients', store=True)
    Edition = fields.Char(related='product_tmpl_id.Edition', store=True)
    is_article = fields.Selection(related='product_tmpl_id.is_article', store=True)

    # Field yang berbeda per variant
    dimension = fields.Char(string="Dimension*")
    gross_weight = fields.Float(string='Gross Weight*')
    net_weight = fields.Float(string='Net Weight*')
    net_net_weight = fields.Float(string='Net Net Weight*')
    date_month_year = fields.Date(string='Date (Month/Year) Design*')

    # =========================
    # PRICE PER VARIANT
    # Override lst_price agar tersimpan di level variant
    # =========================
    lst_price = fields.Float(
        string='Sales Price',
        digits='Product Price',
        default=0.0,
        related=None,   # putus relasi ke template
        store=True,
        readonly=False,
    )

    # =========================
    # CREATE
    # =========================
    @api.model
    def create(self, vals):
        tmpl_id = vals.get('product_tmpl_id')

        if tmpl_id:
            tmpl = self.env['product.template'].browse(tmpl_id)

            if tmpl.is_article == 'yes':
                # ATC: semua variant WAJIB pakai nomor yang sama dengan template
                # Pastikan template sudah punya default_code, jika belum generate
                if not tmpl.default_code:
                    new_code = tmpl._generate_article_number('yes')
                    # Gunakan write langsung ke template (bypass super untuk hindari rekursi)
                    self.env['product.template'].browse(tmpl_id).write({'default_code': new_code})
                    vals['default_code'] = new_code
                else:
                    vals['default_code'] = tmpl.default_code

            elif tmpl.is_article == 'no':
                # PSIT: setiap variant generate nomor unik sendiri
                if not vals.get('default_code'):
                    vals['default_code'] = tmpl._generate_article_number('no')

        return super(ProductProduct, self).create(vals)