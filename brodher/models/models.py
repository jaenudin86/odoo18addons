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
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                (code, tmpl_id)
            )
            template.product_variant_ids.invalidate_recordset(['default_code'])

            @self.env.cr.postcommit.add
            def sync_atc_after_commit():
                with self.env.registry.cursor() as cr:
                    cr.execute(
                        "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                        (code, tmpl_id)
                    )

        elif is_article == 'no':
            tmpl_id = template.id
            env = self.env
            registry = self.env.registry

            self.env.cr.execute(
                "SELECT id FROM product_product WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                (tmpl_id,)
            )
            variant_ids = [r[0] for r in self.env.cr.fetchall()]
            for vid in variant_ids:
                code = self._generate_article_number('no')
                self.env.cr.execute(
                    "UPDATE product_product SET default_code = %s WHERE id = %s",
                    (code, vid)
                )
            if variant_ids:
                template.product_variant_ids.invalidate_recordset(['default_code'])

            @self.env.cr.postcommit.add
            def sync_psit_create_after_commit():
                with registry.cursor() as cr:
                    new_env = api.Environment(cr, env.uid, env.context)
                    cr.execute(
                        "SELECT id, default_code FROM product_product WHERE product_tmpl_id = %s",
                        (tmpl_id,)
                    )
                    all_v = cr.fetchall()
                    _logger.warning(f"[POSTCOMMIT CREATE PSIT] tmpl={tmpl_id} variants={all_v}")
                    empty = [r[0] for r in all_v if not r[1]]
                    for vid in empty:
                        code = new_env['product.template']._generate_article_number('no')
                        cr.execute(
                            "UPDATE product_product SET default_code = %s WHERE id = %s",
                            (code, vid)
                        )
                        _logger.warning(f"[POSTCOMMIT CREATE PSIT] ASSIGNED vid={vid} code={code}")

        return template

    def write(self, vals):
        self.env.cr.execute(
            """SELECT id, default_code, is_article FROM product_template 
               WHERE id = ANY(%s) AND is_article IS NOT NULL""",
            (self.ids,)
        )
        rows = self.env.cr.fetchall()

        atc_codes = {}
        atc_new = []
        psit_ids = []

        for rec_id, code, is_art in rows:
            if is_art == 'yes':
                if code:
                    atc_codes[rec_id] = code
                else:
                    atc_new.append(rec_id)
            elif is_art == 'no':
                psit_ids.append(rec_id)

        _logger.warning(f"[TMPL WRITE] ids={self.ids} atc_codes={atc_codes} atc_new={atc_new} psit_ids={psit_ids}")

        if 'default_code' in vals and not vals.get('default_code') and atc_codes:
            vals = dict(vals)
            vals.pop('default_code')

        if 'is_article' in vals:
            vals['tracking'] = 'serial' if vals['is_article'] == 'yes' else 'none'

        res = super().write(vals)

        # Restore ATC
        for rec_id, code in atc_codes.items():
            self.env.cr.execute(
                "UPDATE product_template SET default_code = %s WHERE id = %s",
                (code, rec_id)
            )
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                (code, rec_id)
            )

        # Sync ATC baru
        for rec_id in atc_new:
            self.env.cr.execute(
                "SELECT default_code FROM product_template WHERE id = %s", (rec_id,)
            )
            row = self.env.cr.fetchone()
            if row and row[0]:
                self.env.cr.execute(
                    "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                    (row[0], rec_id)
                )

        # PSIT: log semua variant dulu
        for rec_id in psit_ids:
            self.env.cr.execute(
                "SELECT id, default_code FROM product_product WHERE product_tmpl_id = %s",
                (rec_id,)
            )
            all_variants = self.env.cr.fetchall()
            _logger.warning(f"[PSIT CHECK] tmpl_id={rec_id} all_variants={all_variants}")

            empty_variants = [r[0] for r in all_variants if not r[1]]
            for vid in empty_variants:
                code = self._generate_article_number('no')
                self.env.cr.execute(
                    "UPDATE product_product SET default_code = %s WHERE id = %s",
                    (code, vid)
                )
                _logger.warning(f"[PSIT CHECK] ASSIGNED vid={vid} code={code}")

        if atc_codes or atc_new or psit_ids:
            self.invalidate_recordset(['default_code'])
            self.mapped('product_variant_ids').invalidate_recordset(['default_code'])

        env = self.env
        registry = self.env.registry
        codes_snapshot = dict(atc_codes)
        atc_new_snapshot = list(atc_new)
        psit_snapshot = list(psit_ids)

        @self.env.cr.postcommit.add
        def restore_after_commit():
            with registry.cursor() as cr:
                new_env = api.Environment(cr, env.uid, env.context)

                # Restore ATC
                for rec_id, code in codes_snapshot.items():
                    cr.execute(
                        "UPDATE product_template SET default_code = %s WHERE id = %s AND (default_code IS NULL OR default_code = '')",
                        (code, rec_id)
                    )
                    cr.execute(
                        "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                        (code, rec_id)
                    )

                # Sync ATC baru
                for rec_id in atc_new_snapshot:
                    cr.execute(
                        "SELECT default_code FROM product_template WHERE id = %s", (rec_id,)
                    )
                    row = cr.fetchone()
                    if row and row[0]:
                        cr.execute(
                            "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                            (row[0], rec_id)
                        )

                # PSIT postcommit
                for rec_id in psit_snapshot:
                    cr.execute(
                        "SELECT id, default_code FROM product_product WHERE product_tmpl_id = %s",
                        (rec_id,)
                    )
                    all_v = cr.fetchall()
                    _logger.warning(f"[POSTCOMMIT PSIT] tmpl={rec_id} variants={all_v}")
                    empty = [r[0] for r in all_v if not r[1]]
                    for vid in empty:
                        code = new_env['product.template']._generate_article_number('no')
                        cr.execute(
                            "UPDATE product_product SET default_code = %s WHERE id = %s",
                            (code, vid)
                        )
                        _logger.warning(f"[POSTCOMMIT PSIT] ASSIGNED vid={vid} code={code}")

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
                    vals['default_code'] = tmpl_code
                    vals['tracking'] = 'serial'
                elif is_article == 'no':
                    if not vals.get('default_code'):
                        tmpl = self.env['product.template'].browse(tmpl_id)
                        vals['default_code'] = tmpl._generate_article_number('no')
                    vals['tracking'] = 'none'

        return super().create(vals)