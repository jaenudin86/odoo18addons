
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import qrcode
import base64
from io import BytesIO


class StockWarehouseCustom(models.Model):
    """
    Inherit stock.warehouse untuk menambahkan custom fields
    File ini bisa digunakan sebagai reference untuk implementasi via Studio
    """
    _inherit = 'stock.warehouse'

    # ==========================================
    # CUSTOM FIELDS - WAREHOUSE CLASSIFICATION
    # ==========================================
    
    x_warehouse_type = fields.Selection([
        ('whc', 'Gudang Pusat (WHC)'),
        ('who', 'Gudang Online (WHO)'),
        ('whs', 'Gudang Offline (WHS)')
    ], string='Warehouse Type', required=True, tracking=True,
       help='Tipe gudang: WHC untuk pusat, WHO untuk online, WHS untuk offline/toko')
    
    x_brand_code = fields.Char(
        string='Brand Code',
        size=3,
        required=True,
        tracking=True,
        help='Kode brand 3 karakter (contoh: MNL, ABC). Harus uppercase.'
    )
    
    x_warehouse_number = fields.Char(
        string='Warehouse Number',
        size=3,
        required=True,
        tracking=True,
        help='Nomor urut warehouse 3 digit (contoh: 001, 002, 003)'
    )
    
    x_warehouse_code_full = fields.Char(
        string='Final Warehouse Code',
        compute='_compute_warehouse_code_full',
        store=True,
        readonly=True,
        tracking=True,
        help='Kode lengkap warehouse (9 digit): TYPE + BRAND + NUMBER'
    )
    
    # ==========================================
    # PRIMARY INFORMATION
    # ==========================================
    
    x_location_name = fields.Char(
        string='Location Name',
        required=True,
        tracking=True,
        help='Nama lokasi warehouse'
    )
    
    x_pic_manager_id = fields.Many2one(
        'res.users',
        string='PIC Warehouse Manager',
        required=True,
        tracking=True,
        help='Manager yang bertanggung jawab atas warehouse ini'
    )
    
    x_email_address = fields.Char(
        string='Email Address',
        required=True,
        tracking=True,
        help='Email PIC warehouse'
    )
    
    x_mobile_phone = fields.Char(
        string='Mobile Phone No',
        required=True,
        tracking=True,
        help='Nomor telepon mobile PIC'
    )
    
    x_location_address = fields.Text(
        string='Location Address',
        required=True,
        tracking=True,
        help='Alamat lengkap warehouse'
    )
    
    x_city_name = fields.Char(
        string='City Name',
        required=True,
        tracking=True,
        help='Nama kota lokasi warehouse'
    )
    
    # ==========================================
    # SECONDARY INFORMATION
    # ==========================================
    
    x_email_address_2 = fields.Char(
        string='Email Address 2',
        tracking=True,
        help='Email alternatif (opsional)'
    )
    
    x_mobile_phone_2 = fields.Char(
        string='Mobile Phone No 2',
        tracking=True,
        help='Nomor telepon alternatif (opsional)'
    )
    
    x_location_address_2 = fields.Text(
        string='Location Address 2',
        tracking=True,
        help='Alamat alternatif (opsional)'
    )
    
    x_city_name_2 = fields.Char(
        string='City Name 2',
        tracking=True,
        help='Kota alternatif (opsional)'
    )
    
    # ==========================================
    # DEPARTMENT STORE INFO (Only for WHS)
    # ==========================================
    
    x_dept_store_name = fields.Char(
        string='Dept Store Name',
        tracking=True,
        help='Nama department store (untuk WHS dalam mall)'
    )
    
    x_dept_store_location = fields.Char(
        string='Dept Store Location',
        tracking=True,
        help='Lokasi dalam department store'
    )
    
    x_pic_dept_store = fields.Char(
        string='PIC Dept Store',
        tracking=True,
        help='Person in charge dari department store'
    )
    
    x_location_name_dept = fields.Char(
        string='Location Name (Dept)',
        tracking=True,
        help='Nama lokasi spesifik dalam department store'
    )
    
    # ==========================================
    # PHOTOS
    # ==========================================
    
    x_front_photo = fields.Binary(
        string='Front Photo',
        attachment=True,
        help='Foto tampak depan warehouse'
    )
    
    x_inside_photo = fields.Binary(
        string='Inside Photo',
        attachment=True,
        help='Foto tampak dalam warehouse'
    )
    
    x_photo_spv_sks = fields.Binary(
        string='Photo SPV and SKS',
        attachment=True,
        help='Foto supervisor dan SKS'
    )
    
    # ==========================================
    # QR CODE
    # ==========================================
    
    x_qr_code = fields.Binary(
        string='QR Code',
        compute='_compute_qr_code',
        store=True,
        attachment=True,
        help='QR Code berisi informasi warehouse'
    )
    
    # ==========================================
    # COMPUTED METHODS
    # ==========================================
    
    @api.depends('x_warehouse_type', 'x_brand_code', 'x_warehouse_number')
    def _compute_warehouse_code_full(self):
        """
        Generate final warehouse code: TYPE + BRAND + NUMBER
        Example: WHCMNL001, WHOMNL002, WHSMNL003
        """
        for record in self:
            if record.x_warehouse_type and record.x_brand_code and record.x_warehouse_number:
                warehouse_type = record.x_warehouse_type.upper()
                brand_code = record.x_brand_code.upper()
                warehouse_no = record.x_warehouse_number.zfill(3)
                
                record.x_warehouse_code_full = f"{warehouse_type}{brand_code}{warehouse_no}"
            else:
                record.x_warehouse_code_full = False
    
    @api.depends('x_warehouse_code_full', 'x_location_name', 'x_pic_manager_id', 'x_mobile_phone')
    def _compute_qr_code(self):
        """
        Generate QR Code with warehouse information
        """
        for record in self:
            if record.x_warehouse_code_full:
                try:
                    # Prepare QR content
                    warehouse_type_label = dict(
                        record._fields['x_warehouse_type'].selection
                    ).get(record.x_warehouse_type, '')
                    
                    qr_content = f"""WAREHOUSE DATABASE
====================
Code: {record.x_warehouse_code_full}
Type: {warehouse_type_label}
Location: {record.x_location_name or ''}
Manager: {record.x_pic_manager_id.name if record.x_pic_manager_id else ''}
Phone: {record.x_mobile_phone or ''}
City: {record.x_city_name or ''}
"""
                    
                    # Generate QR Code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(qr_content)
                    qr.make(fit=True)
                    
                    # Create image
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    # Convert to binary
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    img_bytes = buffer.getvalue()
                    
                    record.x_qr_code = base64.b64encode(img_bytes)
                    
                except Exception as e:
                    # If QR generation fails, just skip it
                    record.x_qr_code = False
            else:
                record.x_qr_code = False
    
    # ==========================================
    # CONSTRAINTS & VALIDATIONS
    # ==========================================
    
    @api.constrains('x_warehouse_type', 'x_brand_code', 'x_warehouse_number')
    def _check_warehouse_code_unique(self):
        """
        Ensure warehouse code is unique
        """
        for record in self:
            if record.x_warehouse_type and record.x_brand_code and record.x_warehouse_number:
                code = f"{record.x_warehouse_type.upper()}{record.x_brand_code.upper()}{record.x_warehouse_number.zfill(3)}"
                
                existing = self.search([
                    ('x_warehouse_code_full', '=', code),
                    ('id', '!=', record.id)
                ])
                
                if existing:
                    raise ValidationError(
                        f"Warehouse code '{code}' already exists! "
                        f"Found in warehouse: {existing.name}"
                    )
    
    @api.constrains('x_brand_code')
    def _check_brand_code_format(self):
        """
        Validate brand code format: must be 3 uppercase letters
        """
        for record in self:
            if record.x_brand_code:
                if len(record.x_brand_code) != 3:
                    raise ValidationError(
                        "Brand code must be exactly 3 characters! "
                        f"Current: '{record.x_brand_code}' ({len(record.x_brand_code)} chars)"
                    )
                
                if not record.x_brand_code.isalpha():
                    raise ValidationError(
                        "Brand code must contain only letters! "
                        f"Current: '{record.x_brand_code}'"
                    )
    
    @api.constrains('x_warehouse_number')
    def _check_warehouse_number_format(self):
        """
        Validate warehouse number format: must be 3 digits
        """
        for record in self:
            if record.x_warehouse_number:
                if len(record.x_warehouse_number) != 3:
                    raise ValidationError(
                        "Warehouse number must be exactly 3 characters! "
                        f"Current: '{record.x_warehouse_number}' ({len(record.x_warehouse_number)} chars)"
                    )
                
                if not record.x_warehouse_number.isdigit():
                    raise ValidationError(
                        "Warehouse number must contain only digits! "
                        f"Current: '{record.x_warehouse_number}'"
                    )
    
    @api.constrains('x_email_address', 'x_email_address_2')
    def _check_email_format(self):
        """
        Validate email format
        """
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for record in self:
            if record.x_email_address:
                if not re.match(email_pattern, record.x_email_address):
                    raise ValidationError(
                        f"Invalid email format: {record.x_email_address}"
                    )
            
            if record.x_email_address_2:
                if not re.match(email_pattern, record.x_email_address_2):
                    raise ValidationError(
                        f"Invalid email format: {record.x_email_address_2}"
                    )
    
    # ==========================================
    # ONCHANGE METHODS
    # ==========================================
    
    @api.onchange('x_brand_code')
    def _onchange_brand_code(self):
        """
        Auto-uppercase brand code
        """
        if self.x_brand_code:
            self.x_brand_code = self.x_brand_code.upper()
    
    @api.onchange('x_pic_manager_id')
    def _onchange_pic_manager(self):
        """
        Auto-fill email and phone from selected user
        """
        if self.x_pic_manager_id:
            if self.x_pic_manager_id.email and not self.x_email_address:
                self.x_email_address = self.x_pic_manager_id.email
            
            if self.x_pic_manager_id.mobile and not self.x_mobile_phone:
                self.x_mobile_phone = self.x_pic_manager_id.mobile
    
    @api.onchange('x_warehouse_type')
    def _onchange_warehouse_type(self):
        """
        Auto-suggest next warehouse number based on type
        """
        if self.x_warehouse_type and not self.x_warehouse_number:
            # Find highest number for this type
            existing_warehouses = self.search([
                ('x_warehouse_type', '=', self.x_warehouse_type)
            ], order='x_warehouse_number desc', limit=1)
            
            if existing_warehouses and existing_warehouses.x_warehouse_number:
                try:
                    last_number = int(existing_warehouses.x_warehouse_number)
                    next_number = last_number + 1
                    self.x_warehouse_number = str(next_number).zfill(3)
                except:
                    pass
            else:
                # Default starting numbers
                default_numbers = {
                    'whc': '001',
                    'who': '002',
                    'whs': '003'
                }
                self.x_warehouse_number = default_numbers.get(self.x_warehouse_type, '001')
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def action_print_warehouse_label(self):
        """
        Print warehouse label with QR code
        """
        return self.env.ref('your_module.action_report_warehouse_label').report_action(self)
    
    def action_view_stock_moves(self):
        """
        View all stock moves for this warehouse
        """
        self.ensure_one()
        return {
            'name': f'Stock Moves - {self.x_warehouse_code_full}',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [
                '|',
                ('location_id.warehouse_id', '=', self.id),
                ('location_dest_id.warehouse_id', '=', self.id)
            ],
            'context': {'default_warehouse_id': self.id}
        }
    
    def action_view_inventory(self):
        """
        View current inventory for this warehouse
        """
        self.ensure_one()
        return {
            'name': f'Inventory - {self.x_warehouse_code_full}',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'tree',
            'domain': [('location_id.warehouse_id', '=', self.id)],
            'context': {'search_default_internal_loc': 1}
        }


class WarehouseTransferRequest(models.Model):
    """
    Model untuk handle transfer request antar warehouse offline (WHS)
    dengan approval workflow
    """
    _name = 'warehouse.transfer.request'
    _description = 'Warehouse Transfer Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char(
        string='Request Number',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )
    
    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Warehouse',
        required=True,
        domain="[('x_warehouse_type', '=', 'whs')]",
        tracking=True
    )
    
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Destination Warehouse',
        required=True,
        domain="[('x_warehouse_type', '=', 'whs'), ('id', '!=', source_warehouse_id)]",
        tracking=True
    )
    
    request_date = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )
    
    product_ids = fields.One2many(
        'warehouse.transfer.request.line',
        'request_id',
        string='Products'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft', required=True, tracking=True)
    
    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        tracking=True,
        help='PIC yang melakukan approval'
    )
    
    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        tracking=True
    )
    
    notes = fields.Text(string='Notes')
    
    rejection_reason = fields.Text(
        string='Rejection Reason',
        tracking=True
    )
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Picking',
        readonly=True,
        help='Stock picking yang dibuat setelah approval'
    )
    
    @api.model
    def create(self, vals):
        """
        Auto-generate sequence number
        """
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'warehouse.transfer.request'
            ) or 'New'
        return super().create(vals)
    
    def action_submit(self):
        """
        Submit for approval
        """
        self.ensure_one()
        if not self.product_ids:
            raise ValidationError("Please add at least one product!")
        
        self.state = 'submitted'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Transfer request submitted for approval',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_approve(self):
        """
        Approve transfer request and create stock picking
        """
        self.ensure_one()
        
        self.state = 'approved'
        self.approver_id = self.env.user
        self.approval_date = fields.Datetime.now()
        
        # Create stock picking
        picking = self._create_stock_picking()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Transfer approved! Picking {picking.name} created.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_reject(self):
        """
        Reject transfer request
        """
        self.ensure_one()
        
        # Open wizard untuk input rejection reason
        return {
            'name': 'Reject Transfer Request',
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.transfer.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }
    
    def action_cancel(self):
        """
        Cancel transfer request
        """
        self.ensure_one()
        self.state = 'cancelled'
    
    def action_set_to_draft(self):
        """
        Reset to draft
        """
        self.ensure_one()
        self.state = 'draft'
    
    def _create_stock_picking(self):
        """
        Create stock picking from approved transfer request
        """
        self.ensure_one()
        
        # Get source and destination locations
        source_location = self.source_warehouse_id.lot_stock_id
        dest_location = self.dest_warehouse_id.lot_stock_id
        
        # Create picking
        picking_vals = {
            'picking_type_id': self.source_warehouse_id.int_type_id.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.name,
            'move_type': 'direct',
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create stock moves for each product
        for line in self.product_ids:
            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
            }
            self.env['stock.move'].create(move_vals)
        
        self.picking_id = picking.id
        
        return picking
    
    def action_view_picking(self):
        """
        View related stock picking
        """
        self.ensure_one()
        return {
            'name': 'Stock Picking',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
        }


class WarehouseTransferRequestLine(models.Model):
    """
    Lines untuk transfer request
    """
    _name = 'warehouse.transfer.request.line'
    _description = 'Warehouse Transfer Request Line'
    
    request_id = fields.Many2one(
        'warehouse.transfer.request',
        string='Transfer Request',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0
    )
    
    available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_available_qty',
        help='Available quantity in source warehouse'
    )
    
    notes = fields.Char(string='Notes')
    
    @api.depends('product_id', 'request_id.source_warehouse_id')
    def _compute_available_qty(self):
        """
        Compute available quantity in source warehouse
        """
        for line in self:
            if line.product_id and line.request_id.source_warehouse_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id.warehouse_id', '=', line.request_id.source_warehouse_id.id),
                    ('location_id.usage', '=', 'internal')
                ])
                line.available_qty = sum(quants.mapped('quantity'))
            else:
                line.available_qty = 0.0
    
    @api.constrains('quantity', 'available_qty')
    def _check_quantity(self):
        """
        Validate quantity tidak melebihi available
        """
        for line in self:
            if line.quantity > line.available_qty:
                raise ValidationError(
                    f"Quantity for {line.product_id.name} ({line.quantity}) "
                    f"exceeds available quantity ({line.available_qty})!"
                )


class WarehouseTransferRejectWizard(models.TransientModel):
    """
    Wizard untuk input rejection reason
    """
    _name = 'warehouse.transfer.reject.wizard'
    _description = 'Reject Transfer Request Wizard'
    
    request_id = fields.Many2one(
        'warehouse.transfer.request',
        string='Transfer Request',
        required=True
    )
    
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True
    )
    
    def action_confirm_reject(self):
        """
        Confirm rejection and update request
        """
        self.ensure_one()
        
        self.request_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })
        
        return {'type': 'ir.actions.act_window_close'}