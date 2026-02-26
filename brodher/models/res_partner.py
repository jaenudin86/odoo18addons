from odoo import api, fields, models
from odoo.exceptions import ValidationError
class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- Penomoran Otomatis ---
    customer_code = fields.Char(string='Customer Code', readonly=True, copy=False)
    supplier_code = fields.Char(string='Supplier Code', readonly=True, copy=False)
    @api.constrains('customer_code')
    def _check_customer_code_unique(self):
        for rec in self:
            if rec.customer_code:
                duplicate = self.search([
                    ('customer_code', '=', rec.customer_code),
                    ('customer_rank', '>', 0),
                    ('id', '!=', rec.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"Customer Code '{rec.customer_code}' sudah digunakan oleh {duplicate.name}!"
                    )

    @api.constrains('supplier_code')
    def _check_supplier_code_unique(self):
        
        for rec in self:
            if rec.supplier_code:
                duplicate = self.search([
                    ('supplier_code', '=', rec.supplier_code),
                    ('supplier_rank', '>', 0),
                    ('id', '!=', rec.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"Supplier Code '{rec.supplier_code}' sudah digunakan oleh {duplicate.name}!"
                    )

    # --- Customer Info ---
    date_of_birth = fields.Date(string='Date of Birth')
    ktp_id = fields.Char(string='Customer ID / KTP')

    # --- Supplier Info ---
    supplier_id_ktp = fields.Char(string="Supplier ID / KTP")
    supplier_product = fields.Char(string="Supplier Product")
    contact_head_pic_name = fields.Char(string="Contact Head PIC Name")
    contact_head_pic_mobile = fields.Char(string="Mobile Phone (Head PIC)")
    contact_pic1_name = fields.Char(string="Contact PIC 1 Name")
    contact_pic1_mobile = fields.Char(string="Mobile Phone (PIC 1)")
    contact_pic2_name = fields.Char(string="Contact PIC 2 Name")
    contact_pic2_mobile = fields.Char(string="Mobile Phone (PIC 2)")

    partner_fax = fields.Char(string="Fax") 
    factory_address = fields.Char(string="Factory Address")
    factory_city = fields.Char(string="Factory City")
    factory_state = fields.Char(string="Factory State")
    factory_postal = fields.Char(string="Factory Postal Code")
    factory_country = fields.Char(string="Factory Country")
    factory_phone = fields.Char(string="Factory Phone")
    factory_fax2 = fields.Char(string="Factory Fax 2")

    supplier_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string="Status", default="active")

    company_profile = fields.Binary(string="Company Profile")

    # --- Bank / Account Info (Supplier) ---
    bank_currency_id = fields.Many2one('res.currency', string="Currency")
    bank_swift = fields.Char(string="Swift Code / Branch")
    bank_city = fields.Char(string="Bank City")
    bank_country = fields.Char(string="Bank Country")
    beneficiary_name = fields.Char(string="Beneficiary Name")

    # --- NPWP Info ---
    npwp_name = fields.Char(string="NPWP Name")
    npwp_address = fields.Text(string="NPWP Address")

    display_name = fields.Char(compute="_compute_display_name", store=True)

    def _compute_display_name(self):
        for rec in self:
            if rec.customer_code:
                rec.display_name = f"{rec.customer_code} - {rec.name}"
            elif rec.supplier_code:
                rec.display_name = f"{rec.supplier_code} - {rec.name}"
            else:
                rec.display_name = rec.name
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # 1. Cek apakah ini Customer
            # Kita cek dari context menu ATAU dari nilai rank yang dikirim UI
            is_customer = self._context.get('res_partner_search_mode') == 'customer' or vals.get('customer_rank', 0) > 0
            
            # 2. Cek apakah ini Supplier
            is_supplier = self._context.get('res_partner_search_mode') == 'supplier' or vals.get('supplier_rank', 0) > 0

            # Eksekusi pembuatan nomor saat Save
            if is_customer and not vals.get('customer_code'):
                seq = self.env['ir.sequence'].next_by_code('customer.code.sequence')
                if seq:
                    vals['customer_code'] = f"AC{seq}"

            if is_supplier and not vals.get('supplier_code'):
                seq = self.env['ir.sequence'].next_by_code('supplier.code.sequence')
                if seq:
                    vals['supplier_code'] = f"AS{seq}"

        return super(ResPartner, self).create(vals_list)

