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
    
    @api.depends('picking_id')
    def _compute_move_summary(self):
        """Show summary of products that will get SNs"""
        for wizard in self:
            if not wizard.picking_id:
                wizard.move_summary = '<p>No transfer selected</p>'
                wizard.total_sn_to_generate = 0
                continue
            
            # Get serial moves
            moves = self.env['stock.move'].search([
                ('picking_id', '=', wizard.picking_id.id),
                ('state', 'not in', ['cancel', 'done']),
                ('product_id', '!=', False),
                ('product_id.tracking', '=', 'serial'),
            ])
            
            if not moves:
                wizard.move_summary = '<p class="text-warning">No products with serial tracking found!</p>'
                wizard.total_sn_to_generate = 0
                continue
            
            # Build HTML summary
            html = '<table class="table table-sm">'
            html += '<thead><tr><th>Product</th><th>Qty</th><th>SN Type</th></tr></thead>'
            html += '<tbody>'
            
            total = 0
            for move in moves:
                qty = int(move.product_uom_qty)
                if qty <= 0:
                    continue
                
                sn_type = 'M'
                if move.product_id.product_tmpl_id:
                    sn_type = getattr(move.product_id.product_tmpl_id, 'sn_product_type', None) or 'M'
                
                sn_type_label = 'Man' if sn_type == 'M' else 'Woman'
                
                html += f'<tr>'
                html += f'<td>{move.product_id.display_name}</td>'
                html += f'<td><strong>{qty}</strong></td>'
                html += f'<td><span class="badge badge-info">{sn_type_label}</span></td>'
                html += f'</tr>'
                
                total += qty
            
            html += '</tbody></table>'
            
            wizard.move_summary = html
            wizard.total_sn_to_generate = total
    
def action_generate_and_close(self):
    """Generate serial numbers - LIMITED by remaining qty"""
    self.ensure_one()
    
    if not self.picking_id:
        raise UserError(_('No transfer specified!'))
    
    if self.picking_id.state not in ['confirmed', 'assigned', 'waiting']:
        raise UserError(_('Transfer must be confirmed!'))
    
    # Get serial moves
    moves = self.env['stock.move'].search([
        ('picking_id', '=', self.picking_id.id),
        ('state', 'not in', ['cancel', 'done']),
        ('product_id', '!=', False),
        ('product_id.tracking', '=', 'serial'),
    ])
    
    if not moves:
        raise UserError(_('No products with serial tracking found!'))
    
    StockLot = self.env['stock.lot']
    total_generated = 0
    generated_details = []
    errors = []
    skipped = []
    
    for move in moves:
        qty_needed = int(move.product_uom_qty)
        
        if qty_needed <= 0:
            continue
        
        # ============================================
        # CHECK: How many SNs already generated?
        # ============================================
        existing_sns = self.env['stock.lot'].search([
            ('product_id', '=', move.product_id.id),
            ('generated_by_picking_id', '=', self.picking_id.id)
        ])
        
        qty_already_generated = len(existing_sns)
        qty_to_generate = qty_needed - qty_already_generated
        
        _logger.info(f'Product: {move.product_id.display_name}, Needed: {qty_needed}, Already: {qty_already_generated}, To Generate: {qty_to_generate}')
        
        if qty_to_generate <= 0:
            skipped.append(f"⊘ {move.product_id.display_name}: Already complete ({qty_already_generated}/{qty_needed} SNs)")
            _logger.info(f'Skipping {move.product_id.display_name} - already has {qty_already_generated} SNs')
            continue
        
        # Get SN type
        sn_type = 'M'
        if move.product_id.product_tmpl_id:
            sn_type = getattr(move.product_id.product_tmpl_id, 'sn_product_type', None) or 'M'
        
        try:
            # Generate ONLY the remaining quantity
            serial_numbers = StockLot.generate_serial_numbers(
                move.product_id.product_tmpl_id.id,
                move.product_id.id,
                sn_type,
                qty_to_generate,  # Only generate what's needed
                picking_id=self.picking_id.id
            )
            
            _logger.info(f'Generated {len(serial_numbers)} SNs for {move.product_id.display_name}')
            
            total_generated += len(serial_numbers)
            
            generated_details.append(f"✓ {move.product_id.display_name}: {len(serial_numbers)} SNs (Type: {sn_type})")
            
            first_sn = serial_numbers[0].name
            last_sn = serial_numbers[-1].name if len(serial_numbers) > 1 else first_sn
            
            if len(serial_numbers) > 1:
                generated_details.append(f"   {first_sn} ... {last_sn}")
            else:
                generated_details.append(f"   {first_sn}")
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f'Error generating SNs: {error_msg}', exc_info=True)
            errors.append(f"✗ {move.product_id.display_name}: {error_msg}")
    
    if total_generated > 0:
        self.picking_id.serial_numbers_generated = True
    
    # Build message
    all_messages = []
    
    if generated_details:
        all_messages.extend(generated_details)
    
    if skipped:
        all_messages.append('\n📋 Already Complete:')
        all_messages.extend(skipped)
    
    if errors:
        all_messages.append('\n❌ Errors:')
        all_messages.extend(errors)
    
    details_message = '\n'.join(all_messages)
    
    if total_generated > 0:
        message = _(
            '✅ Successfully generated %s serial numbers!\n\n'
            '%s\n\n'
            '📝 Serial numbers created in system\n'
            '▶️ Next: Click "Scan Serial Number" to assign them\n'
            '✓ Final: Validate transfer after all SNs scanned'
        ) % (total_generated, details_message)
        msg_type = 'success'
    elif skipped:
        message = _(
            '⚠️ No new serial numbers generated\n\n'
            '%s\n\n'
            'All required serial numbers already exist.'
        ) % details_message
        msg_type = 'warning'
    else:
        message = _('No serial numbers were generated.\n\n%s') % details_message
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