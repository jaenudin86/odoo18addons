# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ProductSNWizard(models.TransientModel):
    _name = 'brodher.product.sn.wizard'
    _description = 'Product Serial Number Generation Wizard'
    
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True)
    product_id = fields.Many2one('product.product', string='Product Variant')
    sn_type = fields.Selection([('M', 'Man'), ('W', 'Woman')], string='Product Type', required=True)
    quantity = fields.Integer(string='Quantity to Generate', default=1, required=True)
    preview_sn = fields.Char(string='Preview Serial Number', compute='_compute_preview_sn', store=False)
    
    @api.depends('sn_type', 'quantity')
    def _compute_preview_sn(self):
        for record in self:
            if record.sn_type:
                try:
                    year = datetime.now().strftime('%y')
                    StockLot = self.env['stock.lot']
                    
                    # Get next sequence GLOBALLY (not per product)
                    next_seq = StockLot._get_next_sequence_global(record.sn_type, year)
                    preview = f"PF{year}{record.sn_type}{next_seq:07d}"
                    
                    if record.quantity > 1:
                        last_seq = next_seq + record.quantity - 1
                        preview += f" ... PF{year}{record.sn_type}{last_seq:07d}"
                    
                    record.preview_sn = preview
                except Exception as e:
                    _logger.warning('Preview computation error: %s' % str(e))
                    record.preview_sn = 'Preview not available'
            else:
                record.preview_sn = ''
    
    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        """Reset product_id when template changes"""
        if self.product_tmpl_id:
            # Auto-select first variant if only one exists
            variants = self.product_tmpl_id.product_variant_ids
            if len(variants) == 1:
                self.product_id = variants[0]
            else:
                self.product_id = False
    
    def action_generate(self):
        """Generate serial numbers with GLOBAL sequencing"""
        _logger.info('=== ACTION GENERATE STARTED ===')
        
        for wizard in self:
            # Validations
            if wizard.quantity <= 0:
                raise UserError(_('Quantity must be greater than 0!'))
            
            if wizard.quantity > 1000:
                raise UserError(_('Cannot generate more than 1000 serial numbers at once!'))
            
            # Determine the actual product to use
            if wizard.product_id:
                product = wizard.product_id
            elif wizard.product_tmpl_id.product_variant_ids:
                product = wizard.product_tmpl_id.product_variant_ids[0]
            else:
                raise UserError(_('No product variant found for the selected template!'))
            
            try:
                StockLot = self.env['stock.lot']
                
                # Generate serial numbers with GLOBAL sequence
                serial_numbers = StockLot.generate_serial_numbers(
                    wizard.product_tmpl_id.id,
                    product.id,
                    wizard.sn_type,
                    wizard.quantity
                )
                
                _logger.info('Generated %d serial numbers for product %s (ID: %d), Type: %s' % 
                           (len(serial_numbers), product.name, product.id, wizard.sn_type))
                
                # Prepare success message
                sn_names = [sn.name for sn in serial_numbers]
                
                if len(serial_numbers) <= 10:
                    sn_list = '\n'.join(sn_names)
                else:
                    sn_list = '\n'.join(sn_names[:10]) + f'\n... and {len(serial_numbers) - 10} more'
                
                # Create message wizard
                message_id = self.env['brodher.message.wizard'].create({
                    'message': _('Successfully generated %d serial numbers for %s:\n\nType: %s\n\n%s') % 
                              (len(serial_numbers), product.display_name, wizard.sn_type, sn_list)
                })
                
                return {
                    'name': _('Success'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'brodher.message.wizard',
                    'res_id': message_id.id,
                    'view_mode': 'form',
                    'target': 'new',
                }
                
            except Exception as e:
                _logger.error('ERROR generating serial numbers: %s' % str(e), exc_info=True)
                raise UserError(_('Error generating serial numbers:\n%s') % str(e))