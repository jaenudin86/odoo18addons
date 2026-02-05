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
    date_month_year = fields.Date()(string='Date (Month/Year) Design')
    # is_article = fields.Boolean(string='Is Article', default=False)

    is_article = fields.Selection(
    [('yes', 'ATC'), ('no', 'PSIT')],
    string="Is Article",
    default='no'
)



    # =========================
    # DEFAULT PRODUCT TYPE = GOODS
    # =========================
    # type = fields.Selection(
    #     selection_add=[],
    #     default='product'
    # )

    # =========================
    # GENERATE ARTICLE NUMBER
    # =========================
    def _generate_article_number(self, is_article):
        """
        - ATC  : ATC + DDMMYY + XXX
        - PSIT : PSIT + YY + XXXX
        """
        now = datetime.today()
        ctx = dict(self._context, ir_sequence_date=now.strftime('%Y-%m-%d'))

        if is_article == 'yes':
            prefix = 'ATC'
            date_str = now.strftime('%d%m%y')
            seq = self.env['ir.sequence'].with_context(ctx)\
                .next_by_code('article.number.sequence') or '001'
            return f"{prefix}{date_str}{seq}"
        else:
            prefix = 'PSIT'
            year_str = now.strftime('%y')
            seq = self.env['ir.sequence'].with_context(ctx)\
                .next_by_code('pist.number.sequence') or '0001'
            return f"{prefix}{year_str}{seq}"

    @api.model
    def create(self, vals):
        # selalu stockable
        vals.setdefault('is_storable', True)
        vals.setdefault('type', 'product')

        # AUTO TRACK INVENTORY
        # if vals.get('is_article') == 'yes':
        #     vals.update({
        #         'is_storable': True,
        #         'tracking': 'serial',   # ATC
        #     })
        # else:
        #     vals.update({
        #         'is_storable': True,
        #         'tracking': 'none',     # PSIT (qty)
        #     })

        return super().create(vals)

    # def write(self, vals):
    #     res = super().write(vals)

    #     if 'is_article' in vals:
    #         for rec in self:
    #             if rec.is_article == 'yes':
    #                 rec.write({
    #                     'is_storable': True,
    #                     'tracking': 'serial',
    #                 })
    #             else:
    #                 rec.write({
    #                     'is_storable': True,
    #                     'tracking': 'none',
    #                 })

    #     return res


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
# psit
    # brand = fields.Char(string="Brand")
    dimension = fields.Char(related='product_tmpl_id.dimension', store=True)
    base_colour = fields.Char(related='product_tmpl_id.base_colour', store=True)
    text_colour = fields.Char(related='product_tmpl_id.text_colour', store=True)
    size = fields.Char(related='product_tmpl_id.size', store=True)
    # size = fields.Char(string="Size")

# atc
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

            # Generate default_code & barcode
            if not vals.get('default_code'):
                code = tmpl._generate_article_number(tmpl.is_article)
                vals.update({
                    'default_code': code,
                    'barcode': code,
                })

            # # KHUSUS ARTICLE → BARCODE STATIS
            # if tmpl.is_article:
            #     size_val = tmpl.size or ""
            #     xx = "".join(re.findall(r'\d+', size_val))
            #     m_char = "M"
            #     name_clean = (tmpl.name or "")[:3].title()

            #     vals['static_barcode'] = f"{xx}{m_char}{name_clean}"

        return super().create(vals)

    # def write(self, vals):
    #     res = super().write(vals)
    #     if 'default_code' in vals:
    #         for rec in self:
    #             if rec.default_code and rec.barcode != rec.default_code:
    #                 rec.barcode = rec.default_code
    #     return res