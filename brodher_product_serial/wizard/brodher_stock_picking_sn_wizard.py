# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class BrodherStockPickingSNWizard(models.TransientModel):
    _name = 'brodher.stock.picking.sn.wizard'
    _description = 'Generate Serial Numbers for Stock Picking'
    
    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True, readonly=True)
    picking_name = fields.Char('Transfer Name', related='picking_id.name', readonly=True)
    
    # Add editable lines
    line_ids = fields.One2many(
        'brodher.stock.picking.sn.wizard.line',
        'wizard_id',
        string='Products'
    )
    
    move_summary = fields.Html('Products to Generate', compute='_compute_move_summary')
    total_sn_to_generate = fields.Integer('Total SNs', compute='_compute_move_summary')
    
    @api.depends('line_ids.quantity')
    def _compute_move_summary(self):
        """Show summary based on editable lines"""
        for wizard in self:
            if not wizard.line_ids:
                wizard.move_summary = '<p>No products to generate</p>'
                wizard.total_sn_to_generate = 0
                continue
            
            # Build HTML summary from lines
            html = '<table class="table table-sm">'
            html += '<thead><tr><th>Product</th><th>Demand</th><th>Already Gen</th><th>To Generate</th><th>SN Type</th></tr></thead>'
            html += '<tbody>'
            
            total = 0
            for line in wizard.line_ids:
                sn_type_label = 'Man' if line.sn_type == 'M' else 'Woman'
                
                html += '<tr>'
                html += f'<td>{line.product_name}</td>'
                html += f'<td>{line.quantity_in_picking}</td>'
                html += f'<td>{line.quantity_existing}</td>'
                html += f'<td><strong style="color: green;">{line.quantity}</strong></td>'
                html += f'<td><span class="badge badge-info">{sn_type_label}</span></td>'
                html += '</tr>'
                
                total += line.quantity
            
            html += '</tbody></table>'
            
            wizard.move_summary = html
            wizard.total_sn_to_generate = total
    
    @api.model
    def default_get(self, fields_list):
        """Populate wizard with editable lines"""
        res = super(BrodherStockPickingSNWizard, self).default_get(fields_list)
        
        picking_id = self.env.context.get('default_picking_id')
        if not picking_id:
            return res
        
        picking = self.env['stock.picking'].browse(picking_id)
        
        # Get serial moves
        moves = self.env['stock.move'].search([
            ('picking_id', '=', picking.id),
            ('state', 'not in', ['cancel', 'done']),
            ('product_id', '!=', False),
            ('product_id.tracking', '=', 'serial'),
        ])
        
        if not moves:
            return res
        
        lines = []
        for move in moves:
            qty_needed = int(move.product_uom_qty)
            if qty_needed <= 0:
                continue
            
            # Check already generated
            existing_sns = self.env['stock.lot'].search([
                ('product_id', '=', move.product_id.id),
                ('generated_by_picking_id', '=', picking.id)
            ])
            qty_existing = len(existing_sns)
            qty_to_generate = max(0, qty_needed - qty_existing)
            
            # Get SN type
            sn_type = 'M'
            if move.product_id.product_tmpl_id:
                sn_type = getattr(move.product_id.product_tmpl_id, 'sn_product_type', None) or 'M'
            
            lines.append((0, 0, {
                'product_id': move.product_id.id,
                'product_name': move.product_id.display_name,
                'quantity_in_picking': qty_needed,
                'quantity_existing': qty_existing,
                'quantity': qty_to_generate,  # Default: remaining qty
                'sn_type': sn_type,
            }))
        
        if lines:
            res['line_ids'] = lines
        
        return res
    
    def action_generate_and_close(self):
        """Generate serial numbers based on editable lines"""
        self.ensure_one()
        
        if not self.picking_id:
            raise UserError(_('No transfer specified!'))
        
        if self.picking_id.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_('Transfer must be confirmed!'))
        
        if self.total_sn_to_generate == 0:
            raise UserError(_('No serial numbers to generate!\n\nPlease set quantity > 0 for at least one product.'))
        
        StockLot = self.env['stock.lot']
        total_generated = 0
        generated_details = []
        errors = []
        
        for line in self.line_ids.filtered(lambda l: l.quantity > 0):
            try:
                # Validate max qty
                max_allowed = line.quantity_in_picking - line.quantity_existing
                if line.quantity > max_allowed:
                    raise UserError(_(
                        'Cannot generate %s SNs for %s!\n\n'
                        'Maximum: %s (Demand: %s, Already: %s)'
                    ) % (line.quantity, line.product_name, max_allowed,
                         line.quantity_in_picking, line.quantity_existing))
                
                # Generate SNs
                serial_numbers = StockLot.generate_serial_numbers(
                    line.product_id.product_tmpl_id.id,
                    line.product_id.id,
                    line.sn_type,
                    line.quantity,
                    picking_id=self.picking_id.id
                )
                
                _logger.info(f'Generated {len(serial_numbers)} SNs for {line.product_name}')
                
                total_generated += len(serial_numbers)
                
                generated_details.append(f"✓ {line.product_name}: {len(serial_numbers)} SNs (Type: {line.sn_type})")
                
                first_sn = serial_numbers[0].name
                last_sn = serial_numbers[-1].name if len(serial_numbers) > 1 else first_sn
                
                if len(serial_numbers) > 1:
                    generated_details.append(f"   {first_sn} ... {last_sn}")
                else:
                    generated_details.append(f"   {first_sn}")
                
            except Exception as e:
                error_msg = str(e)
                _logger.error(f'Error: {error_msg}', exc_info=True)
                errors.append(f"✗ {line.product_name}: {error_msg}")
        
        if total_generated > 0:
            self.picking_id.serial_numbers_generated = True
        
        details_message = '\n'.join(generated_details)
        
        if errors:
            details_message += '\n\n❌ Errors:\n' + '\n'.join(errors)
        
        if total_generated > 0:
            message = _(
                '✅ Successfully generated %s serial numbers!\n\n'
                '%s\n\n'
                '📝 SNs created in system\n'
                '▶️ Next: Click "Scan Serial Number" to assign them'
            ) % (total_generated, details_message)
            msg_type = 'success'
        else:
            message = _('No serial numbers generated.\n\n%s') % details_message
            msg_type = 'warning'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generation Complete'),
                'message': message,
                'type': msg_type,
                'sticky': True,
            }
        }


class BrodherStockPickingSNWizardLine(models.TransientModel):
    _name = 'brodher.stock.picking.sn.wizard.line'
    _description = 'SN Generation Line'
    
    wizard_id = fields.Many2one('brodher.stock.picking.sn.wizard', required=True, ondelete='cascade')
    
    product_id = fields.Many2one('product.product', required=True, readonly=True)
    product_name = fields.Char('Product', readonly=True)
    
    quantity_in_picking = fields.Integer('Demand', readonly=True)
    quantity_existing = fields.Integer('Already Gen', readonly=True)
    quantity = fields.Integer('To Generate', required=True, default=0)
    
    sn_type = fields.Selection([
        ('M', 'Man'),
        ('W', 'Woman')
    ], string='Type', required=True, readonly=True)
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_('Quantity cannot be negative!'))
            
            max_qty = line.quantity_in_picking - line.quantity_existing
            if line.quantity > max_qty:
                raise ValidationError(_(
                    'Cannot generate more than %s SNs for %s!'
                ) % (max_qty, line.product_name))