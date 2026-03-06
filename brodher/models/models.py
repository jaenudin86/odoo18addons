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

    # ══════════════════════════════════════════════════════════════════════════
    # HARGA JUAL — tampilkan dari variant pertama, tidak sebar ke semua variant
    # ══════════════════════════════════════════════════════════════════════════
    lst_price = fields.Float(
        string='Sales Price',
        digits='Product Price',
        compute='_compute_template_lst_price',
        inverse='_set_template_lst_price',
        store=False,
    )

    def _compute_template_lst_price(self):
        for tmpl in self:
            variants = tmpl.product_variant_ids
            tmpl.lst_price = variants[0].lst_price if variants else 0.0

    def _set_template_lst_price(self):
        """Hanya isi variant yang belum ada harga (0.0). Tidak timpa yang sudah diisi."""
        for tmpl in self:
            for variant in tmpl.product_variant_ids:
                if variant.lst_price == 0.0:
                    variant.lst_price = tmpl.lst_price

    # ══════════════════════════════════════════════════════════════════════════
    # HARGA MODAL — tampilkan dari variant pertama, tidak sebar ke semua variant
    # ══════════════════════════════════════════════════════════════════════════
    standard_price = fields.Float(
        string='Cost',
        digits='Product Price',
        compute='_compute_template_standard_price',
        inverse='_set_template_standard_price',
        store=False,
    )

    def _compute_template_standard_price(self):
        for tmpl in self:
            variants = tmpl.with_context(force_company=self.env.company.id).product_variant_ids
            tmpl.standard_price = variants[0].standard_price if variants else 0.0

    def _set_template_standard_price(self):
        """Hanya isi variant yang belum ada harga modal (0.0)."""
        for tmpl in self:
            for variant in tmpl.product_variant_ids:
                if variant.standard_price == 0.0:
                    variant.standard_price = tmpl.standard_price

    # ══════════════════════════════════════════════════════════════════════════
    # PAJAK PENJUALAN — tampilkan dari variant pertama
    # ══════════════════════════════════════════════════════════════════════════
    taxes_id = fields.Many2many(
        'account.tax',
        string='Customer Taxes',
        compute='_compute_template_taxes',
        inverse='_set_template_taxes',
        store=False,
        domain=[('type_tax_use', '=', 'sale')],
    )

    def _compute_template_taxes(self):
        for tmpl in self:
            variants = tmpl.product_variant_ids
            tmpl.taxes_id = variants[0].taxes_id if variants else False

    def _set_template_taxes(self):
        """Hanya isi variant yang belum punya pajak jual."""
        for tmpl in self:
            for variant in tmpl.product_variant_ids:
                if not variant.taxes_id:
                    variant.taxes_id = tmpl.taxes_id

    # ══════════════════════════════════════════════════════════════════════════
    # PAJAK PEMBELIAN — tampilkan dari variant pertama
    # ══════════════════════════════════════════════════════════════════════════
    supplier_taxes_id = fields.Many2many(
        'account.tax',
        string='Vendor Taxes',
        compute='_compute_template_supplier_taxes',
        inverse='_set_template_supplier_taxes',
        store=False,
        domain=[('type_tax_use', '=', 'purchase')],
    )

    def _compute_template_supplier_taxes(self):
        for tmpl in self:
            variants = tmpl.product_variant_ids
            tmpl.supplier_taxes_id = variants[0].supplier_taxes_id if variants else False

    def _set_template_supplier_taxes(self):
        """Hanya isi variant yang belum punya pajak beli."""
        for tmpl in self:
            for variant in tmpl.product_variant_ids:
                if not variant.supplier_taxes_id:
                    variant.supplier_taxes_id = tmpl.supplier_taxes_id

    # ══════════════════════════════════════════════════════════════════════════

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

    def _compute_default_code(self):
        for template in self:
            if template.is_article in ('yes', 'no'):
                self.env.cr.execute(
                    "SELECT default_code FROM product_template WHERE id = %s",
                    (template.id,)
                )
                row = self.env.cr.fetchone()
                template.default_code = row[0] if row and row[0] else False
            else:
                super(ProductTemplate, template)._compute_default_code()

    @api.model
    def create(self, vals):
        vals.setdefault('is_storable', True)
        vals.setdefault('type', 'product')
        is_article = vals.get('is_article', 'no')

        if is_article == 'yes':
            vals['tracking'] = 'serial'
            if not (vals.get('default_code') or '').strip():
                vals['default_code'] = self._generate_article_number('yes')
        elif is_article == 'no':
            vals['tracking'] = 'none'
            if not (vals.get('default_code') or '').strip():
                vals['default_code'] = self._generate_article_number('no')

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
            empty_variants = [r[0] for r in self.env.cr.fetchall()]
            for vid in empty_variants:
                code = self._generate_article_number('no')
                self.env.cr.execute(
                    "UPDATE product_product SET default_code = %s WHERE id = %s",
                    (code, vid)
                )

            if empty_variants:
                template.product_variant_ids.invalidate_recordset(['default_code'])
                template.invalidate_recordset(['default_code'])

            @self.env.cr.postcommit.add
            def sync_psit_after_commit():
                with registry.cursor() as cr:
                    new_env = api.Environment(cr, env.uid, env.context)
                    cr.execute(
                        "SELECT id FROM product_product WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                        (tmpl_id,)
                    )
                    empty = [r[0] for r in cr.fetchall()]
                    for vid in empty:
                        code = new_env['product.template']._generate_article_number('no')
                        cr.execute(
                            "UPDATE product_product SET default_code = %s WHERE id = %s",
                            (code, vid)
                        )

        return template

    def write(self, vals):
        self.env.cr.execute(
            """SELECT id, default_code FROM product_template 
               WHERE id = ANY(%s) AND is_article = 'yes'
               AND default_code IS NOT NULL AND default_code != ''""",
            (self.ids,)
        )
        atc_codes = dict(self.env.cr.fetchall())

        if 'default_code' in vals and not vals.get('default_code') and atc_codes:
            vals = dict(vals)
            vals.pop('default_code')

        if 'is_article' in vals:
            vals['tracking'] = 'serial' if vals['is_article'] == 'yes' else 'none'

        res = super().write(vals)

        for rec_id, code in atc_codes.items():
            self.env.cr.execute(
                "UPDATE product_template SET default_code = %s WHERE id = %s",
                (code, rec_id)
            )
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                (code, rec_id)
            )

        self.env.cr.execute(
            "SELECT id FROM product_template WHERE id = ANY(%s) AND is_article = 'no'",
            (self.ids,)
        )
        psit_tmpl_ids = [r[0] for r in self.env.cr.fetchall()]

        for rec_id in psit_tmpl_ids:
            self.env.cr.execute(
                "SELECT id FROM product_product WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                (rec_id,)
            )
            empty_variants = [r[0] for r in self.env.cr.fetchall()]
            for vid in empty_variants:
                code = self._generate_article_number('no')
                self.env.cr.execute(
                    "UPDATE product_product SET default_code = %s WHERE id = %s",
                    (code, vid)
                )

        if atc_codes or psit_tmpl_ids:
            self.invalidate_recordset(['default_code'])
            self.mapped('product_variant_ids').invalidate_recordset(['default_code'])

        env = self.env
        registry = self.env.registry
        codes_snapshot = dict(atc_codes)
        psit_snapshot = list(psit_tmpl_ids)

        @self.env.cr.postcommit.add
        def restore_after_commit():
            with registry.cursor() as cr:
                new_env = api.Environment(cr, env.uid, env.context)

                for rec_id, code in codes_snapshot.items():
                    cr.execute(
                        "UPDATE product_template SET default_code = %s WHERE id = %s AND (default_code IS NULL OR default_code = '')",
                        (code, rec_id)
                    )
                    cr.execute(
                        "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                        (code, rec_id)
                    )

                for rec_id in psit_snapshot:
                    cr.execute(
                        "SELECT id FROM product_product WHERE product_tmpl_id = %s AND (default_code IS NULL OR default_code = '')",
                        (rec_id,)
                    )
                    empty = [r[0] for r in cr.fetchall()]
                    for vid in empty:
                        code = new_env['product.template']._generate_article_number('no')
                        cr.execute(
                            "UPDATE product_product SET default_code = %s WHERE id = %s",
                            (code, vid)
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

    # ══════════════════════════════════════════════════════════════════════════
    # HARGA JUAL — independen per variant
    # ══════════════════════════════════════════════════════════════════════════
    lst_price = fields.Float(
        string='Sales Price / Harga Jual',
        digits='Product Price',
        default=0.0,
        related=None,
        store=True,
        readonly=False,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # HARGA MODAL — independen per variant
    # company_dependent=True sudah built-in di Odoo untuk standard_price,
    # kita override agar bisa diinput langsung di form variant.
    # ══════════════════════════════════════════════════════════════════════════
    standard_price = fields.Float(
        string='Cost / Harga Modal',
        digits='Product Price',
        default=0.0,
        company_dependent=True,
        store=True,
        readonly=False,
        groups="base.group_user",
    )

    # ══════════════════════════════════════════════════════════════════════════
    # PAJAK PENJUALAN — independen per variant
    # Menggunakan relation table tersendiri agar tidak konflik dgn template
    # ══════════════════════════════════════════════════════════════════════════
    taxes_id = fields.Many2many(
        'account.tax',
        'product_variant_taxes_rel',
        'prod_id',
        'tax_id',
        string='Customer Taxes / Pajak Jual',
        domain=[('type_tax_use', '=', 'sale')],
        store=True,
        readonly=False,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # PAJAK PEMBELIAN — independen per variant
    # Menggunakan relation table tersendiri agar tidak konflik dgn template
    # ══════════════════════════════════════════════════════════════════════════
    supplier_taxes_id = fields.Many2many(
        'account.tax',
        'product_variant_supplier_taxes_rel',
        'prod_id',
        'tax_id',
        string='Vendor Taxes / Pajak Beli',
        domain=[('type_tax_use', '=', 'purchase')],
        store=True,
        readonly=False,
    )

    # ══════════════════════════════════════════════════════════════════════════

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