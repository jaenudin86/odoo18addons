# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

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
            self.env.cr.execute(
                """UPDATE product_product
                   SET lst_price = %s
                   WHERE product_tmpl_id = %s
                   AND (lst_price IS NULL OR lst_price = 0.0)""",
                (tmpl.lst_price, tmpl.id)
            )
            tmpl.product_variant_ids.invalidate_recordset(['lst_price'])

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
    # VALIDASI NAMA PRODUK TIDAK BOLEH DUPLIKAT (level template)
    # ══════════════════════════════════════════════════════════════════════════
    @api.constrains('name')
    def _check_unique_product_name(self):
        for tmpl in self:
            duplicate = self.env['product.template'].search([
                ('name', '=ilike', tmpl.name),
                ('id', '!=', tmpl.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f'Nama produk "{tmpl.name}" sudah digunakan oleh produk lain! '
                    f'Silakan gunakan nama yang berbeda.'
                )


    @api.constrains('attribute_line_ids')
    def _check_attribute_line_ids(self):
        for tmpl in self:
            if not tmpl.attribute_line_ids:
                raise ValidationError('Tab "Attributes & Variants" (Atribut dan Varian) wajib diisi!')


    @api.onchange('name')
    def _onchange_name_check_duplicate(self):
        """Warning real-time saat user mengetik nama yang sudah ada."""
        if self.name:
            duplicate = self.env['product.template'].search([
                ('name', '=ilike', self.name),
                ('id', '!=', self._origin.id or 0),
            ], limit=1)
            if duplicate:
                return {
                    'warning': {
                        'title': 'Nama Sudah Digunakan!',
                        'message': f'Produk dengan nama "{self.name}" sudah ada. Silakan gunakan nama lain.',
                    }
                }

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
            # ATC: template dan semua variant pakai nomor yang sama
            vals['tracking'] = 'serial'
            if not (vals.get('default_code') or '').strip():
                vals['default_code'] = self._generate_article_number('yes')

        elif is_article == 'no':
            # PSIT: template TIDAK dapat nomor otomatis, dibiarkan kosong
            vals['tracking'] = 'none'
            vals.pop('default_code', None)  # pastikan template tidak dapat nomor

        template = super().create(vals)

        if is_article == 'yes' and template.default_code:
            # ATC: sinkronkan nomor template ke semua variant
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
            # PSIT: hanya variant yang dapat nomor otomatis, template tetap kosong
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
                # Jangan invalidate default_code template agar tetap kosong
                self.env.cr.execute(
                    "UPDATE product_template SET default_code = NULL WHERE id = %s",
                    (tmpl_id,)
                )

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
            # PSIT: pastikan default_code template tetap NULL/kosong
            self.env.cr.execute(
                "UPDATE product_template SET default_code = NULL WHERE id = %s",
                (rec_id,)
            )
            # Hanya variant yang dapat nomor otomatis
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
                    # PSIT post-commit: pastikan template tetap kosong
                    cr.execute(
                        "UPDATE product_template SET default_code = NULL WHERE id = %s",
                        (rec_id,)
                    )
                    # Variant yang belum punya nomor → generate
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

        self._check_duplicate_variants()

        return res

    def _check_duplicate_variants(self):
        """
        Dipanggil setelah write pada template.
        Cek semua variant yang terbentuk — tidak boleh ada display_name yang sama.
        """
        from odoo.exceptions import ValidationError
        for tmpl in self:
            variants = tmpl.product_variant_ids
            names = [v.display_name for v in variants]
            duplicates = [n for n in names if names.count(n) > 1]
            if duplicates:
                dup_list = ', '.join(set(duplicates))
                raise ValidationError(
                    f'Variant duplikat ditemukan: "{dup_list}". '
                    f'Setiap kombinasi atribut harus unik!'
                )


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
        compute='_compute_product_lst_price',
        inverse='_set_product_lst_price',
        store=True,
        readonly=False,
    )

    def _compute_product_lst_price(self):
        """Baca harga dari kolom product_product (per variant), bukan dari template."""
        for product in self:
            self.env.cr.execute(
                "SELECT lst_price FROM product_product WHERE id = %s",
                (product.id,)
            )
            row = self.env.cr.fetchone()
            product.lst_price = row[0] if row and row[0] is not None else 0.0

    def _set_product_lst_price(self):
        """Simpan harga langsung ke baris product_product (per variant)."""
        for product in self:
            self.env.cr.execute(
                "UPDATE product_product SET lst_price = %s WHERE id = %s",
                (product.lst_price, product.id)
            )
            product.invalidate_recordset(['lst_price'])

    # ══════════════════════════════════════════════════════════════════════════
    # HARGA MODAL — independen per variant
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
    # VALIDASI NAMA VARIANT TIDAK BOLEH DUPLIKAT
    # ══════════════════════════════════════════════════════════════════════════
    def _check_unique_variant_name(self):
        """Cek semua variant dalam satu template, tidak boleh ada nama yang sama."""
        for variant in self:
            siblings = variant.product_tmpl_id.product_variant_ids.filtered(
                lambda v: v.id != variant.id
            )
            variant_name = variant.display_name
            for sibling in siblings:
                if sibling.display_name == variant_name:
                    raise ValidationError(
                        f'Nama variant "{variant_name}" sudah ada! '
                        f'Setiap variant harus memiliki kombinasi atribut yang unik.'
                    )


    @api.constrains('product_template_variant_value_ids')
    def _check_variant_values(self):
        for product in self:
            if not product.product_template_variant_value_ids:
                raise ValidationError('Varian wajib memiliki atribut yang dipilih!')


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
                    # ATC: variant ikut nomor template
                    vals['default_code'] = tmpl_code
                    vals['tracking'] = 'serial'
                elif is_article == 'no':
                    # PSIT: variant dapat nomor otomatis sendiri, tracking none
                    vals['tracking'] = 'none'
                    if not vals.get('default_code'):
                        tmpl = self.env['product.template'].browse(tmpl_id)
                        vals['default_code'] = tmpl._generate_article_number('no')

        return super().create(vals)