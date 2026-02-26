from odoo import models, fields, api


class ProductQrcodeLabelWizard(models.TransientModel):
    _name = 'product.qrcode.label.wizard'
    _description = 'Product QR Code Label Wizard'

    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        required=True
    )
    quantity = fields.Integer(
        string='Quantity per Product',
        default=1,
        required=True,
        help='Number of labels to print for each product'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])
        
        if active_model == 'product.product' and active_ids:
            res['product_ids'] = [(6, 0, active_ids)]
        elif active_model == 'product.template' and active_ids:
            templates = self.env['product.template'].browse(active_ids)
            variant_ids = templates.mapped('product_variant_ids').ids
            res['product_ids'] = [(6, 0, variant_ids)]
        
        return res

    def action_print_labels(self):
        """Generate and print QR code labels"""
        self.ensure_one()
        return self.env.ref('brodher_product_serial.action_report_product_qrcode_label').report_action(self)