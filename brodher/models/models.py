# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime


class ProductTemplate(models.Model):
    _inherit = 'product.template'

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

    @api.onchange('is_article')
    def _onchange_is_article(self):
        if self.is_article in ['yes', 'no']:
            self.default_code = ''

    @api.onchange('is_article')
    def _onchange_is_article_tracking(self):
        if self.is_article == 'yes':
            self.tracking = 'serial'
        else:
            self.tracking = 'none'

    @api.onchange('parent_article_id')
    def _onchange_parent_article(self):
        if self.is_article == 'var' and self.parent_article_id:
            self.default_code = self.parent_article_id.default_code

    def _generate_article_number(self, is_article):
        now = datetime.today()
        ctx = dict(self._context, ir_sequence_date=now.strftime('%Y-%m-%d'))
        if is_article == 'yes':
            date_str = now.strftime('%d%m%y')
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code('article.number.sequence') or '001'
            return f"ATC{date_str}{str(seq).zfill(3)}"
        else:
            year_str = now.strftime('%y')
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code('psit.number.sequence') or '0001'
            return f"PSIT{year_str}{str(seq).zfill(4)}"

    @api.model
    def create(self, vals):
        vals.setdefault('is_storable', True)
        vals.setdefault('type', 'product')

        is_article = vals.get('is_article', 'no')

        if is_article == 'yes':
            vals['tracking'] = 'serial'
            if not vals.get('default_code', '').strip() if vals.get('default_code') else True:
                vals['default_code'] = self._generate_article_number('yes')
        else:
            vals['tracking'] = 'none'
            vals['default_code'] = False

        template = super(ProductTemplate, self).create(vals)

        # Sync ke variant — pakai raw SQL agar tidak trigger rekursi
        if is_article == 'yes' and template.default_code:
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                (template.default_code, template.id)
            )
            self.env.cr.execute(
                "UPDATE product_product SET tracking = 'serial' WHERE product_tmpl_id = %s",
                (template.id,)
            )
            template.product_variant_ids.invalidate_recordset(['default_code', 'tracking'])
        elif is_article == 'no':
            self.env.cr.execute(
                "UPDATE product_product SET tracking = 'none' WHERE product_tmpl_id = %s",
                (template.id,)
            )
            template.product_variant_ids.invalidate_recordset(['tracking'])

        return template

    def write(self, vals):
        # Simpan default_code lama untuk ATC sebelum write
        atc_codes = {}
        for rec in self:
            if rec.is_article == 'yes' and rec.default_code:
                atc_codes[rec.id] = rec.default_code

        # Jangan izinkan default_code ATC di-clear via vals
        if 'default_code' in vals and not vals.get('default_code'):
            atc_ids = [rid for rid in atc_codes]
            if atc_ids and all(r.id in atc_ids for r in self):
                vals.pop('default_code')

        if 'is_article' in vals:
            vals['tracking'] = 'serial' if vals['is_article'] == 'yes' else 'none'

        res = super(ProductTemplate, self).write(vals)

        for rec in self:
            if rec.is_article == 'yes':
                # Pastikan default_code template tidak hilang
                expected_code = vals.get('default_code') or atc_codes.get(rec.id) or rec.default_code
                if expected_code:
                    # Sync ke semua variant via raw SQL (hindari rekursi)
                    self.env.cr.execute(
                        "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                        (expected_code, rec.id)
                    )
                    self.env.cr.execute(
                        "UPDATE product_product SET tracking = 'serial' WHERE product_tmpl_id = %s",
                        (rec.id,)
                    )
                    rec.product_variant_ids.invalidate_recordset(['default_code', 'tracking'])

                    # Restore default_code template jika hilang
                    if not rec.default_code:
                        self.env.cr.execute(
                            "UPDATE product_template SET default_code = %s WHERE id = %s",
                            (expected_code, rec.id)
                        )
                        rec.invalidate_recordset(['default_code'])

            elif rec.is_article == 'no' and 'is_article' in vals:
                self.env.cr.execute(
                    "UPDATE product_product SET default_code = NULL, tracking = 'none' WHERE product_tmpl_id = %s",
                    (rec.id,)
                )
                rec.product_variant_ids.invalidate_recordset(['default_code', 'tracking'])

        return res

    def _create_variant_ids(self):
        """Sync default_code ATC ke variant baru yang di-generate Odoo"""
        res = super(ProductTemplate, self)._create_variant_ids()
        for template in self:
            if template.is_article == 'yes' and template.default_code:
                self.env.cr.execute(
                    "UPDATE product_product SET default_code = %s, tracking = 'serial' WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                    (template.default_code, template.id)
                )
                template.product_variant_ids.invalidate_recordset(['default_code', 'tracking'])
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    static_barcode = fields.Char(string='Barcode Statis', readonly=True)

    brand = fields.Char(related='product_tmpl_id.brand', store=True)
    base_colour = fields.Char(related='product_tmpl_id.base_colour', store=True)
    text_colour = fields.Char(related='product_tmpl_id.text_colour', store=True)
    size = fields.Char(related='product_tmpl_id.size', store=True)
    ingredients = fields.Text(related='product_tmpl_id.ingredients', store=True)
    Edition = fields.Char(related='product_tmpl_id.Edition', store=True)
    is_article = fields.Selection(related='product_tmpl_id.is_article', store=True)

    dimension = fields.Char(string="Dimension*")
    gross_weight = fields.Float(string='Gross Weight*')
    net_weight = fields.Float(string='Net Weight*')
    net_net_weight = fields.Float(string='Net Net Weight*')
    date_month_year = fields.Date(string='Date (Month/Year) Design*')

    lst_price = fields.Float(
        string='Sales Price',
        digits='Product Price',
        default=0.0,
        related=None,
        store=True,
        readonly=False,
    )

    @api.model
    def create(self, vals):
        tmpl_id = vals.get('product_tmpl_id')
        if tmpl_id:
            tmpl = self.env['product.template'].browse(tmpl_id)
            if tmpl.is_article == 'yes':
                # Selalu ikut default_code template — TIDAK generate baru
                vals['default_code'] = tmpl.default_code or ''
                vals['tracking'] = 'serial'
            elif tmpl.is_article == 'no':
                if not vals.get('default_code'):
                    vals['default_code'] = tmpl._generate_article_number('no')
                vals['tracking'] = 'none'

        product = super(ProductProduct, self).create(vals)

        # Safety check setelah create
        if tmpl_id:
            tmpl = self.env['product.template'].browse(tmpl_id)
            if tmpl.is_article == 'yes' and tmpl.default_code:
                if product.default_code != tmpl.default_code:
                    self.env.cr.execute(
                        "UPDATE product_product SET default_code = %s WHERE id = %s",
                        (tmpl.default_code, product.id)
                    )
                    product.invalidate_recordset(['default_code'])

        return product

    # TIDAK ADA write() override di ProductProduct
    # Semua dikontrol dari ProductTemplate