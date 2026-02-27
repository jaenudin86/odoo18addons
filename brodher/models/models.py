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

    @api.onchange('is_article')
    def _onchange_is_article_tracking(self):
        if self.is_article == 'yes':
            self.tracking = 'serial'
        else:
            self.tracking = 'none'

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

        if is_article == 'yes':
            vals['tracking'] = 'serial'
        else:
            vals['tracking'] = 'none'

        if is_article == 'yes':
            default_code = vals.get('default_code')
            if not default_code or (isinstance(default_code, str) and not default_code.strip()):
                vals['default_code'] = self._generate_article_number('yes')
        else:
            vals['default_code'] = False

        template = super(ProductTemplate, self).create(vals)

        if is_article == 'yes':
            template.product_variant_ids.write({
                'default_code': template.default_code,
                'tracking': 'serial',
            })
        else:
            template.product_variant_ids.write({
                'tracking': 'none',
            })

        return template

    # =========================
    # WRITE
    # =========================
    def write(self, vals):
        if 'is_article' in vals:
            new_tracking = 'serial' if vals['is_article'] == 'yes' else 'none'
            vals['tracking'] = new_tracking

        res = super(ProductTemplate, self).write(vals)

        for rec in self:
            if 'is_article' in vals:
                new_tracking = 'serial' if rec.is_article == 'yes' else 'none'
                rec.product_variant_ids.write({'tracking': new_tracking})

                if rec.is_article == 'no':
                    rec.product_variant_ids.write({'default_code': False})

            if 'default_code' in vals and rec.is_article == 'yes':
                rec.product_variant_ids.write({'default_code': vals['default_code']})

            # TAMBAHAN: Sync default_code ke variant baru yang belum punya
            if rec.is_article == 'yes' and rec.default_code:
                variants_without_code = rec.product_variant_ids.filtered(
                    lambda v: not v.default_code or v.default_code != rec.default_code
                )
                if variants_without_code:
                    for variant in variants_without_code:
                        self.env.cr.execute(
                            "UPDATE product_product SET default_code = %s WHERE id = %s",
                            (rec.default_code, variant.id)
                        )
                    variants_without_code.invalidate_recordset(['default_code'])

        return res

    # =========================
    # OVERRIDE _CREATE_VARIANT_IDS
    # Handle saat Odoo auto-generate variant baru
    # =========================
    def _create_variant_ids(self):
        """Override untuk sync default_code ATC ke variant yang baru di-generate Odoo"""
        res = super(ProductTemplate, self)._create_variant_ids()

        for template in self:
            if template.is_article == 'yes' and template.default_code:
                variants_without_code = template.product_variant_ids.filtered(
                    lambda v: not v.default_code or v.default_code != template.default_code
                )
                if variants_without_code:
                    for variant in variants_without_code:
                        self.env.cr.execute(
                            "UPDATE product_product SET default_code = %s WHERE id = %s",
                            (template.default_code, variant.id)
                        )
                    variants_without_code.invalidate_recordset(['default_code'])

                # Pastikan tracking semua variant ATC = serial
                template.product_variant_ids.filtered(
                    lambda v: v.tracking != 'serial'
                ).write({'tracking': 'serial'})

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
    # =========================
    lst_price = fields.Float(
        string='Sales Price',
        digits='Product Price',
        default=0.0,
        related=None,
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
                if not tmpl.default_code:
                    new_code = tmpl._generate_article_number('yes')
                    tmpl.write({'default_code': new_code})
                    vals['default_code'] = new_code
                else:
                    vals['default_code'] = tmpl.default_code
                vals['tracking'] = 'serial'

            elif tmpl.is_article == 'no':
                if not vals.get('default_code'):
                    vals['default_code'] = tmpl._generate_article_number('no')
                vals['tracking'] = 'none'

        product = super(ProductProduct, self).create(vals)

        # Extra safety: force sync setelah create
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

    # =========================
    # WRITE
    # =========================
    def write(self, vals):
        res = super(ProductProduct, self).write(vals)

        # Jika default_code di-clear atau berubah di variant ATC,
        # kembalikan ke default_code template
        for product in self:
            if product.is_article == 'yes':
                tmpl_code = product.product_tmpl_id.default_code
                if tmpl_code and product.default_code != tmpl_code:
                    self.env.cr.execute(
                        "UPDATE product_product SET default_code = %s WHERE id = %s",
                        (tmpl_code, product.id)
                    )
                    product.invalidate_recordset(['default_code'])

        return res