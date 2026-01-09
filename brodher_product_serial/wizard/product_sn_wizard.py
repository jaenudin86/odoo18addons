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
                    # Memanggil fungsi sequence global tanpa filter product_id
                    next_seq = self.env['stock.lot']._get_next_sequence(record.sn_type)
                    
                    preview = f"PF{year}{record.sn_type}{next_seq:07d}"
                    if record.quantity > 1:
                        last_seq = next_seq + record.quantity - 1
                        preview += f" ... PF{year}{record.sn_type}{last_seq:07d}"
                    record.preview_sn = preview
                except Exception as e:
                    _logger.error("Preview Error: %s" % str(e))
                    record.preview_sn = 'Preview not available'
            else:
                record.preview_sn = ''
    
    def action_generate(self):
        _logger.info('=== ACTION GENERATE STARTED ===')
        for wizard in self:
            if wizard.quantity <= 0:
                raise UserError(_('Quantity must be greater than 0!'))
            if wizard.quantity > 1000:
                raise UserError(_('Cannot generate more than 1000 serial numbers at once!'))
            
            try:
                # Menjalankan fungsi generate yang sudah diperbarui di stock.lot
                serial_numbers = self.env['stock.lot'].generate_serial_numbers(
                    wizard.product_tmpl_id.id,
                    wizard.product_id.id if wizard.product_id else False,
                    wizard.sn_type,
                    wizard.quantity
                )
                
                sn_names = [sn.name for sn in serial_numbers]
                if len(serial_numbers) <= 10:
                    sn_list = '\n'.join(sn_names)
                else:
                    sn_list = '\n'.join(sn_names[:10]) + f'\n... and {len(serial_numbers) - 10} more'
                
                message_id = self.env['brodher.message.wizard'].create({
                    'message': _('Successfully generated %d serial numbers:\n\n%s') % (len(serial_numbers), sn_list)
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
                _logger.error('ERROR: %s' % str(e))
                raise UserError(_('Error generating serial numbers:\n%s') % str(e))