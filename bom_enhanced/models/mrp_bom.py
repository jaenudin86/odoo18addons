from odoo import models, fields, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    serial_number = fields.Char(
        string='Serial Number',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help='Unique serial number for BOM identification'
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        help='Related sales order reference (optional)',
        copy=False
    )
    
    sale_order_name = fields.Char(
        related='sale_order_id.name',
        string='SO Number',
        readonly=True,
        store=True
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('serial_number', 'New') == 'New':
                vals['serial_number'] = self.env['ir.sequence'].next_by_code('mrp.bom.serial') or 'New'
        return super(MrpBom, self).create(vals_list)
    
    def action_print_bom_with_price(self):
        """Print BOM report with prices"""
        return self.env.ref('bom_enhanced.action_report_bom_with_price').report_action(self)
    
    def action_print_bom_no_price(self):
        """Print BOM report without prices"""
        return self.env.ref('bom_enhanced.action_report_bom_no_price').report_action(self)
