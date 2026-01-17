from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- Penomoran Otomatis ---
    customer_code = fields.Char(string='Customer Code', readonly=True, copy=False)
    supplier_code = fields.Char(string='Supplier Code', readonly=True, copy=False)

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Generate Customer Code (AC + 7 digit = 9 digit)
            # Logika: Jika sedang membuat customer
            if vals.get('customer_rank', 0) > 0 or self._context.get('res_partner_search_mode') == 'customer':
                if not vals.get('customer_code'):
                    seq = self.env['ir.sequence'].next_by_code('customer.code.sequence')
                    vals['customer_code'] = f'AC{seq}'

            # Generate Supplier Code (AS + 4 digit = 6 digit)
            # Logika: Jika sedang membuat supplier
            if vals.get('supplier_rank', 0) > 0 or self._context.get('res_partner_search_mode') == 'supplier':
                if not vals.get('supplier_code'):
                    seq = self.env['ir.sequence'].next_by_code('supplier.code.sequence')
                    vals['supplier_code'] = f'AS{seq}'
                    
        return super(ResPartner, self).create(vals_list)