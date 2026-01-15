# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class BrodherStockPickingSNWizard(models.TransientModel):
    _name = 'brodher.stock.picking.sn.wizard'
    _description = 'Generate Serial Numbers for Stock Picking'
    
    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True, readonly=True)
    picking_name = fields.Char('Transfer Name', related='picking_id.name', readonly=True)
    
    move_summary = fields.Html('Products to Generate', compute='_compute_move_summary')
    total_sn_to_generate = fields.Integer('Total SNs', compute='_compute_move_summary')
    
    # Add lines for per-product qty control
    line_ids = fields.One2many(
        'brodher.stock.picking.sn.wizard.line',
        'wizard_id',
        string='Products'
    )
    
    @api.depends('line_ids.quantity')
    def _compute_move_summary(self):
        """Show summary with editable quantities"""
        for wizard in self:
            if not wizard.line_ids:
                wizard.move_summary = '<p class="text-muted">No products to generate</p>'
                wizard.total_sn_to_generate = 0
                continue
            
            html = '<table class="table table-sm table-bordered">'
            html += '<thead class="table-light"><tr>'
            html += '<th>Product</th>'
            html += '<th class="text-center">Demand</th>'
            html += '<th class="text-center">Already Generated</th>'
            html += '<th class="text-center">To Generate</th>'
            html += '<th class="text-center">SN Type</th>'
            html += '</tr></thead><tbody>'
            
            total = 0
            for line in wizard.line_ids:
                sn_type_label = 'Man' if line.sn_type == 'M' else 'Woman'
                
                html += '<tr>'
                html += f'<td><strong>{line.product_name}</strong></td>'
                html += f'<td class="text-center">{line.quantity_in_picking}</td>'
                html += f'<td class="text-center">{line.quantity_existing}</td>'
                html += f'<td class="text-center"><strong style="color: green;">{line.quantity}</strong></td>'
                html += f'<td class="text-center"><span class="badge badge-info">{sn_type_label}</span></td>'
                html += '</tr>'
                
                total += line.quantity
            
            html += '</tbody></table>'
            
            wizard.move_summary = html
            wizard.total_sn_to_generate = total
    
    @api.model
    def default_get(self, fields_list):
        """Populate wizard with products and editable quantities"""
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
            
            # Check how many already generated
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
                'quantity': qty_to_generate,  # Default: generate remaining
                'sn_type': sn_type,
            }))
        
        if lines:
            res['line_ids'] = lines
        
        return res
    
    def action_generate_and_close(self):
        """Generate serial numbers based on user input"""
        self.ensure_one()
        
        if not self.picking_id:
            raise UserError(_('No transfer specified!'))
        
        if self.total_sn_to_generate == 0:
            raise UserError(_('No serial numbers to generate!\n\nPlease set quantity > 0 for at least one product.'))
        
        StockLot = self.env['stock.lot']
        total_generated = 0
        generated_details = []
        errors = []
        
        for line in self.line_ids.filtered(lambda l: l.quantity > 0):
            try:
                # Check max limit
                max_allowed = line.quantity_in_picking - line.quantity_existing
                if line.quantity > max_allowed:
                    raise UserError(_(
                        'Cannot generate %s SNs for %s!\n\n'
                        'Maximum allowed: %s (Demand: %s, Already: %s)'
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
                
                _logger.info(f'[WIZARD] Generated {len(serial_numbers)} SNs for {line.product_name}')
                
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
                _logger.error(f'Error generating SNs: {error_msg}', exc_info=True)
                errors.append(f"✗ {line.product_name}: {error_msg}")
        
        if total_generated > 0:
            self.picking_id.serial_numbers_generated = True
        
        details_message = '\n'.join(generated_details)
        
        if errors:
            details_message += '\n\nErrors:\n' + '\n'.join(errors)
        
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
    
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    product_name = fields.Char('Product Name', readonly=True)
    
    quantity_in_picking = fields.Integer('Demand', readonly=True)
    quantity_existing = fields.Integer('Already Generated', readonly=True)
    quantity = fields.Integer('Qty to Generate', required=True, default=1)
    
    sn_type = fields.Selection([
        ('M', 'Man'),
        ('W', 'Woman')
    ], string='SN Type', required=True, default='M', readonly=True)
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_('Quantity cannot be negative!'))
            
            max_qty = line.quantity_in_picking - line.quantity_existing
            if line.quantity > max_qty:
                raise ValidationError(_(
                    'Cannot generate more than %s SNs!\n\n'
                    'Demand: %s\n'
                    'Already Generated: %s\n'
                    'Maximum: %s'
                ) % (max_qty, line.quantity_in_picking, line.quantity_existing, max_qty))