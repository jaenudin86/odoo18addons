# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductQrcodeLabelWizard(models.TransientModel):
    _name = 'product.qrcode.label.wizard'
    _description = 'Product QR Code Label Wizard'
    
    product_ids = fields.Many2many(
        'product.product',
        'product_qr_wizard_product_rel',
        'wizard_id',
        'product_id',
        string='Products',
        required=True
    )
    
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        help='Set jika dibuka dari product template'
    )
    
    variant_ids = fields.Many2many(
        'product.product',
        'product_qr_wizard_variant_rel',
        'wizard_id',
        'variant_id',
        string='Select Variants',
        help='Pilih variant tertentu. Kosongkan untuk cetak semua variant.'
    )
    
    variant_count = fields.Integer(
        string='Variant Count',
        compute='_compute_variant_count',
        help='Jumlah variant dari product template'
    )
    
    quantity = fields.Integer(
        string='Quantity per Product',
        default=1,
        required=True,
        help='Number of labels to print for each product'
    )
    
    total_labels = fields.Integer(
        string='Total Labels',
        compute='_compute_total_labels',
        help='Total jumlah label yang akan dicetak'
    )
    
    @api.depends('product_tmpl_id')
    def _compute_variant_count(self):
        """Count variants of product template"""
        for wizard in self:
            if wizard.product_tmpl_id:
                wizard.variant_count = len(wizard.product_tmpl_id.product_variant_ids)
            else:
                wizard.variant_count = 0
    
    @api.depends('product_ids', 'variant_ids', 'product_tmpl_id', 'quantity')
    def _compute_total_labels(self):
        """Calculate total labels to print"""
        for wizard in self:
            # Determine which products will be printed
            if wizard.variant_ids:
                # User selected specific variants
                count = len(wizard.variant_ids)
            elif wizard.product_tmpl_id:
                # All variants of template
                count = len(wizard.product_tmpl_id.product_variant_ids)
            else:
                # Selected products
                count = len(wizard.product_ids)
            
            wizard.total_labels = count * wizard.quantity
    
    @api.model
    def default_get(self, fields_list):
        """Populate based on context"""
        res = super(ProductQrcodeLabelWizard, self).default_get(fields_list)
        
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])
        active_id = self.env.context.get('active_id')
        
        # Opened from product.product (variants)
        if active_model == 'product.product' and active_ids:
            res['product_ids'] = [(6, 0, active_ids)]
        
        # Opened from product.template
        elif active_model == 'product.template' and active_id:
            template = self.env['product.template'].browse(active_id)
            res['product_tmpl_id'] = active_id
            res['product_ids'] = [(6, 0, template.product_variant_ids.ids)]
        
        return res
    
    def action_print_labels(self):
        """Generate and print QR code labels"""
        self.ensure_one()
        
        # Determine which products to print
        if self.variant_ids:
            # User selected specific variants
            products_to_print = self.variant_ids
        elif self.product_tmpl_id:
            # All variants of template
            products_to_print = self.product_tmpl_id.product_variant_ids
        else:
            # Selected products
            products_to_print = self.product_ids
        
        # Duplicate products by quantity
        product_list = []
        for product in products_to_print:
            for i in range(self.quantity):
                product_list.append(product.id)
        
        # Create recordset for printing
        products_recordset = self.env['product.product'].browse(product_list)
        
        # Generate report
        return self.env.ref('brodher_product_serial.action_report_product_qrcode_label').report_action(
            products_recordset
        )