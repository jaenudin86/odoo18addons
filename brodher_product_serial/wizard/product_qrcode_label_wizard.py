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
    
    variant_ids = fields.Many2many(
        'product.product',
        'product_qr_wizard_variant_rel',
        'wizard_id',
        'variant_id',
        string='Select Variants',
        help='Pilih variant tertentu. Kosongkan untuk cetak semua.'
    )
    
    show_variant_selection = fields.Boolean(
        string='Show Variant Selection',
        compute='_compute_show_variant_selection',
        help='Show variant selection if multiple variants from same template'
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
    
    @api.depends('product_ids')
    def _compute_show_variant_selection(self):
        """Show variant selection if products are from same template"""
        for wizard in self:
            if len(wizard.product_ids) > 0:
                # Check if all products are from the same template
                templates = wizard.product_ids.mapped('product_tmpl_id')
                wizard.show_variant_selection = (len(templates) == 1 and len(wizard.product_ids) > 1)
            else:
                wizard.show_variant_selection = False
    
    @api.depends('product_ids', 'variant_ids', 'quantity')
    def _compute_total_labels(self):
        """Calculate total labels to print"""
        for wizard in self:
            # If specific variants selected, use those
            if wizard.variant_ids:
                count = len(wizard.variant_ids)
            else:
                # Use all products
                count = len(wizard.product_ids)
            
            wizard.total_labels = count * wizard.quantity
    
    @api.model
    def default_get(self, fields_list):
        """Populate based on context"""
        res = super(ProductQrcodeLabelWizard, self).default_get(fields_list)
        
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])
        
        # From product.product (variants)
        if active_model == 'product.product' and active_ids:
            res['product_ids'] = [(6, 0, active_ids)]
        
        # From product.template
        elif active_model == 'product.template' and active_ids:
            templates = self.env['product.template'].browse(active_ids)
            variant_ids = templates.mapped('product_variant_ids').ids
            res['product_ids'] = [(6, 0, variant_ids)]
        
        return res
    
    def action_print_labels(self):
        """Generate and print QR code labels"""
        self.ensure_one()
        
        # Determine which products to print
        if self.variant_ids:
            products_to_print = self.variant_ids
        else:
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