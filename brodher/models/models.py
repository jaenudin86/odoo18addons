# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


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
        self.tracking = 'serial' if self.is_article == 'yes' else 'none'

    @api.onchange('parent_article_id')
    def _onchange_parent_article(self):
        if self.is_article == 'var' and self.parent_article_id:
            self.default_code = self.parent_article_id.default_code

    def _generate_article_number(self, is_article):
        now = datetime.today()
        ctx = dict(self._context, ir_sequence_date=now.strftime('%Y-%m-%d'))
        if is_article == 'yes':
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code('article.number.sequence') or '001'
            return f"ATC{now.strftime('%d%m%y')}{str(seq).zfill(3)}"
        else:
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code('psit.number.sequence') or '0001'
            return f"PSIT{now.strftime('%y')}{str(seq).zfill(4)}"

    @api.model
    def create(self, vals):
        vals.setdefault('is_storable', True)
        vals.setdefault('type', 'product')
        is_article = vals.get('is_article', 'no')

        if is_article == 'yes':
            vals['tracking'] = 'serial'
            if not (vals.get('default_code') or '').strip():
                vals['default_code'] = self._generate_article_number('yes')
        else:
            vals['tracking'] = 'none'
            vals['default_code'] = False

        template = super().create(vals)

        if is_article == 'yes' and template.default_code:
            code = template.default_code
            tmpl_id = template.id
            # Sync langsung ke semua variant
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                (code, tmpl_id)
            )
            template.product_variant_ids.invalidate_recordset(['default_code'])

            # Sync lagi setelah commit — handle create + variant sekaligus
            @self.env.cr.postcommit.add
            def sync_atc_after_commit():
                with self.env.registry.cursor() as cr:
                    cr.execute(
                        "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                        (code, tmpl_id)
                    )

        return template

    def write(self, vals):
        # Ambil hanya ATC codes dari DB
        self.env.cr.execute(
            """SELECT id, default_code FROM product_template 
               WHERE id = ANY(%s) 
               AND is_article = 'yes'
               AND default_code IS NOT NULL 
               AND default_code != ''""",
            (self.ids,)
        )
        atc_codes = dict(self.env.cr.fetchall())

        _logger.warning(f"[TMPL WRITE] ids={self.ids} atc_codes={atc_codes}")

        # Jangan izinkan default_code ATC di-clear
        if 'default_code' in vals and not vals.get('default_code') and atc_codes:
            vals = dict(vals)
            vals.pop('default_code')
            _logger.warning(f"[TMPL WRITE] REMOVED default_code from vals")

        if 'is_article' in vals:
            vals['tracking'] = 'serial' if vals['is_article'] == 'yes' else 'none'

        res = super().write(vals)

        # Restore ATC codes — sync ke template dan semua variant
        for rec_id, code in atc_codes.items():
            self.env.cr.execute(
                "UPDATE product_template SET default_code = %s WHERE id = %s",
                (code, rec_id)
            )
            # ATC: semua variant pakai kode yang sama
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                (code, rec_id)
            )
            _logger.warning(f"[TMPL WRITE] RESTORED ATC id={rec_id} code={code}")

        if atc_codes:
            self.invalidate_recordset(['default_code'])
            self.mapped('product_variant_ids').invalidate_recordset(['default_code'])

            # Postcommit untuk ATC
            @self.env.cr.postcommit.add
            def restore_atc_after_commit():
                with self.env.registry.cursor() as cr:
                    for rec_id, code in atc_codes.items():
                        cr.execute(
                            "UPDATE product_template SET default_code = %s WHERE id = %s AND (default_code IS NULL OR default_code = '')",
                            (code, rec_id)
                        )
                        cr.execute(
                            "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                            (code, rec_id)
                        )

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
            self.env.cr.execute(
                "SELECT is_article, default_code FROM product_template WHERE id = %s",
                (tmpl_id,)
            )
            row = self.env.cr.fetchone()
            if row:
                is_article, tmpl_code = row
                if is_article == 'yes':
                    # ATC: ikut kode template
                    vals['default_code'] = tmpl_code
                    vals['tracking'] = 'serial'
                elif is_article == 'no':
                    # PSIT: generate nomor unik baru untuk setiap variant
                    if not vals.get('default_code'):
                        tmpl = self.env['product.template'].browse(tmpl_id)
                        vals['default_code'] = tmpl._generate_article_number('no')
                    vals['tracking'] = 'none'

        return super().create(vals)