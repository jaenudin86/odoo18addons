# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime

_logger = __import__('logging').getLogger(__name__)


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

    def _sync_default_code_to_variants(self, code):
        """Sync default_code ke semua variant via raw SQL untuk menghindari rekursi"""
        if not code:
            return
        variant_ids = self.product_variant_ids.ids
        if variant_ids:
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE id = ANY(%s)",
                (code, variant_ids)
            )
            self.product_variant_ids.invalidate_recordset(['default_code'])

    @api.model
    def create(self, vals):
        vals.setdefault('is_storable', True)
        vals.setdefault('type', 'product')

        is_article = vals.get('is_article', 'no')

        if is_article == 'yes':
            vals['tracking'] = 'serial'
            default_code = vals.get('default_code')
            if not default_code or (isinstance(default_code, str) and not default_code.strip()):
                vals['default_code'] = self._generate_article_number('yes')
        else:
            vals['tracking'] = 'none'
            vals['default_code'] = False

        template = super(ProductTemplate, self).create(vals)

        if is_article == 'yes':
            template._sync_default_code_to_variants(template.default_code)
            template.product_variant_ids.write({'tracking': 'serial'})
        else:
            template.product_variant_ids.write({'tracking': 'none'})

        return template

    def write(self, vals):
        # ================================================================
        # GUARD: Cegah default_code ATC di-clear
        # Cek SEBELUM super() agar kita tahu nilai lama
        # ================================================================
        if 'default_code' in vals:
            for rec in self:
                if rec.is_article == 'yes' and not vals.get('default_code'):
                    # Hapus dari vals — jangan izinkan clear default_code ATC
                    vals = {k: v for k, v in vals.items() if k != 'default_code'}
                    break

        if 'is_article' in vals:
            vals['tracking'] = 'serial' if vals['is_article'] == 'yes' else 'none'

        res = super(ProductTemplate, self).write(vals)

        for rec in self:
            if 'is_article' in vals:
                new_tracking = 'serial' if rec.is_article == 'yes' else 'none'
                rec.product_variant_ids.write({'tracking': new_tracking})
                if rec.is_article == 'no':
                    self.env.cr.execute(
                        "UPDATE product_product SET default_code = NULL WHERE id = ANY(%s)",
                        (rec.product_variant_ids.ids,)
                    )
                    rec.product_variant_ids.invalidate_recordset(['default_code'])

            # Sync default_code ke variant ATC via raw SQL (hindari rekursi)
            if 'default_code' in vals and rec.is_article == 'yes' and vals.get('default_code'):
                rec._sync_default_code_to_variants(vals['default_code'])

            # Pastikan variant ATC yang belum punya default_code di-sync
            if rec.is_article == 'yes' and rec.default_code:
                missing = [v.id for v in rec.product_variant_ids if not v.default_code]
                if missing:
                    self.env.cr.execute(
                        "UPDATE product_product SET default_code = %s WHERE id = ANY(%s)",
                        (rec.default_code, missing)
                    )
                    rec.product_variant_ids.invalidate_recordset(['default_code'])

        return res

    def _create_variant_ids(self):
        """Override untuk sync default_code ATC ke variant baru yang di-generate Odoo"""
        res = super(ProductTemplate, self)._create_variant_ids()
        for template in self:
            if template.is_article == 'yes' and template.default_code:
                template._sync_default_code_to_variants(template.default_code)
                needs_tracking = template.product_variant_ids.filtered(
                    lambda v: v.tracking != 'serial'
                )
                if needs_tracking:
                    needs_tracking.write({'tracking': 'serial'})
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
                if not tmpl.default_code:
                    new_code = tmpl._generate_article_number('yes')
                    # Gunakan raw SQL untuk set default_code di template
                    # agar tidak trigger write() rekursif
                    self.env.cr.execute(
                        "UPDATE product_template SET default_code = %s WHERE id = %s",
                        (new_code, tmpl_id)
                    )
                    tmpl.invalidate_recordset(['default_code'])
                    vals['default_code'] = new_code
                else:
                    vals['default_code'] = tmpl.default_code
                vals['tracking'] = 'serial'

            elif tmpl.is_article == 'no':
                if not vals.get('default_code'):
                    vals['default_code'] = tmpl._generate_article_number('no')
                vals['tracking'] = 'none'

        product = super(ProductProduct, self).create(vals)

        # Extra safety: pastikan default_code ATC tersimpan
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