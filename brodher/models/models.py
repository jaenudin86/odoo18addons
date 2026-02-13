# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # =========================
    # FIELD TAMBAHAN
    # =========================
    # psit
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

    # atc
    ingredients = fields.Text(string="Ingredients*")
    Edition = fields.Char(string="Edition*")     
    gross_weight = fields.Float(string='Gross Weight*')
    net_weight = fields.Float(string='Net Weight*')
    net_net_weight = fields.Float(string='Net Net Weight*')
    date_month_year = fields.Date(string='Date (Month/Year) Design*')

    is_article = fields.Selection(
        [('yes', 'ATC'),('var', 'ATC Variant'), ('no', 'PSIT')],
        string="Is Article",
        default='no'
    )

    # =========================
    # ONCHANGE METHODS
    # =========================
    @api.onchange('is_article')
    def _onchange_is_article(self):
        """Reset default_code ketika is_article berubah ke yes atau no"""
        if self.is_article in ['yes', 'no']:
            self.default_code = ''

    @api.onchange('parent_article_id')
    def _onchange_parent_article(self):
        """ Jika memilih parent, ambil default_code-nya """
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

        if is_article == 'yes' or is_article == 'var':
            prefix = 'ATC'
            date_str = now.strftime('%d%m%y')
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code('article.number.sequence') or '001'
            seq = str(seq).zfill(3)
            return f"{prefix}{date_str}{seq}"
        else:
            prefix = 'PSIT'
            year_str = now.strftime('%y')
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code('pist.number.sequence') or '0001'
            seq = str(seq).zfill(4)
            return f"{prefix}{year_str}{seq}"

    @api.model
    def create(self, vals):
        # Selalu storable/stockable
        vals.setdefault('is_storable', True)
        vals.setdefault('type', 'product')

        # AUTO TRACK INVENTORY
        if vals.get('is_article') == 'yes' or vals.get('is_article') == 'var':
            vals.update({'tracking': 'serial'})
        else:
            vals.update({'tracking': 'none'})

        # Generate default_code di level template (Nomor Pertama)
        if not vals.get('default_code'):
            is_article = vals.get('is_article', 'no')
            vals['default_code'] = self._generate_article_number(is_article)

        return super(ProductTemplate, self).create(vals)

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        # Update tracking di varian jika is_article berubah
        if 'is_article' in vals:
            for rec in self:
                new_tracking = 'serial' if rec.is_article == 'yes' or rec.is_article == 'var' else 'none'
                rec.product_variant_ids.write({'tracking': new_tracking})
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    static_barcode = fields.Char(string='Barcode Statis', readonly=True)

    # =========================
    # RELATED FIELDS (Agar tersimpan di DB/Store=True)
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

    @api.onchange('is_article')
    def _onchange_is_article(self):
        """Reset default_code ketika is_article berubah ke yes atau no"""
        if self.is_article in ['yes', 'no']:
            self.default_code = ''

    @api.model
    def create(self, vals):
        tmpl_id = vals.get('product_tmpl_id')
        
        if tmpl_id:
            tmpl = self.env['product.template'].browse(tmpl_id)
            
            # Cek apakah sudah ada varian lain untuk template ini
            existing_variant = self.search_count([('product_tmpl_id', '=', tmpl_id)])
            
            if not vals.get('default_code'):
                if existing_variant == 0:
                    # VARIANT PERTAMA: Ambil nomor dari template agar tidak loncat
                    vals['default_code'] = tmpl.default_code
                    # vals['barcode'] = tmpl.default_code
                else:
                    # VARIANT KEDUA dst: Baru panggil sequence untuk nomor baru
                    new_code = tmpl._generate_article_number(tmpl.is_article)
                    vals['default_code'] = new_code
                    # vals['barcode'] = new_code
            
            # Sinkronisasi barcode jika default_code diisi manual
            # elif not vals.get('barcode'):
            #     vals['barcode'] = vals.get('default_code')

        return super(ProductProduct, self).create(vals)