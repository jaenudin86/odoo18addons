# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductQRCodeLabelWizard(models.TransientModel):
    _name = 'product.qrcode.label.wizard'
    _description = 'Product QR Code Label Wizard'
    
    product_ids = fields.Many2many(
        'product.product', 
        string='Products',
        help='Products to print labels for'
    )
    
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        help='Product template if opened from template'
    )
    
    variant_ids = fields.Many2many(
        'product.product',
        'product_qr_wizard_variant_rel',
        'wizard_id',
        'product_id',
        string='Select Variants',
        help='Pilih variant yang ingin dicetak. Kosongkan untuk cetak semua variant.'
    )
    
    quantity = fields.Integer(
        string='Quantity per Product',
        default=1,
        required=True,
        help='Number of labels to print per product/variant'
    )
    
    @api.model
    def default_get(self, fields_list):
        """Populate products based on context"""
        res = super(ProductQRCodeLabelWizard, self).default_get(fields_list)
        
        # Check if called from product.product (variant)
        if self.env.context.get('active_model') == 'product.product':
            active_ids = self.env.context.get('active_ids', [])
            if active_ids:
                res['product_ids'] = [(6, 0, active_ids)]
        
        # Check if called from product.template
        elif self.env.context.get('active_model') == 'product.template':
            active_id = self.env.context.get('active_id')
            if active_id:
                product_tmpl = self.env['product.template'].browse(active_id)
                res['product_tmpl_id'] = active_id
                # Get all variants of this template
                res['product_ids'] = [(6, 0, product_tmpl.product_variant_ids.ids)]
        
        return res
    
    def action_print_labels(self):
        """Generate QR code labels"""
        self.ensure_one()
        
        # Determine which products to print
        if self.variant_ids:
            # User selected specific variants
            products_to_print = self.variant_ids
        elif self.product_tmpl_id:
            # Print all variants of template
            products_to_print = self.product_tmpl_id.product_variant_ids
        else:
            # Print selected products
            products_to_print = self.product_ids
        
        if not products_to_print:
            raise UserError(_('No products selected to print!'))
        
        # Pass data to report
        data = {
            'product_ids': products_to_print.ids,
            'quantity': self.quantity,
        }
        
        # Generate report
        return self.env.ref('your_module.action_report_product_qrcode').report_action(
            products_to_print, 
            data=data
        )
