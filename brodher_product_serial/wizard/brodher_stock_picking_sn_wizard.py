# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class BrodherStockPickingSNWizard(models.TransientModel):
    _name = 'brodher.stock.picking.sn.wizard'
    _description = 'Generate Serial Numbers for Stock Picking'
    
    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True, readonly=True)
    picking_name = fields.Char('Transfer Name', related='picking_id.name', readonly=True)
    operation_type = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
        ('internal', 'Internal Transfer')
    ], string='Operation Type', readonly=True)
    
    line_ids = fields.One2many('brodher.stock.picking.sn.wizard.line', 'wizard_id', string='Products')
    
    total_to_generate = fields.Integer('Total to Generate', compute='_compute_totals')
    total_products = fields.Integer('Total Products', compute='_compute_totals')
    can_generate = fields.Boolean('Can Generate', compute='_compute_totals')
    
    @api.depends('line_ids.quantity', 'line_ids.generate')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_products = len(wizard.line_ids)
            wizard.total_to_generate = sum(
                line.quantity for line in wizard.line_ids if line.generate
            )
            wizard.can_generate = wizard.total_to_generate > 0
    
    @api.model
    def default_get(self, fields_list):
        """Override default_get - ensure moves have real IDs"""
        res = super(BrodherStockPickingSNWizard, self).default_get(fields_list)
        
        picking_id = self.env.context.get('default_picking_id') or self.env.context.get('active_id')
        
        if not picking_id:
            raise UserError(_('No transfer ID provided!'))
        
        # ==========================================
        # CRITICAL: Force flush to ensure moves are saved
        # ==========================================
        self.env.flush_all()
        
        picking = self.env['stock.picking'].browse(picking_id)
        
        if not picking.exists():
            raise UserError(_('Transfer not found!'))
        
        _logger.info(f'[WIZARD] Opening for: {picking.name}, state: {picking.state}')
        
        # Validate state
        if picking.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_(
                '❌ Cannot generate serial numbers!\n\n'
                'Transfer state: %s\n\n'
                'Please click "Mark as Todo" first.'
            ) % picking.state)
        
        # ==========================================
        # Get moves using SEARCH (most reliable)
        # ==========================================
        all_moves = self.env['stock.move'].search([
            ('picking_id', '=', picking.id),
            ('state', 'not in', ['cancel', 'done']),
        ])
        
        _logger.info(f'[WIZARD] Found {len(all_moves)} total moves')
        
        # Filter for serial + SN type
        serial_moves = all_moves.filtered(
            lambda m: m.product_id and
                     m.product_id.tracking == 'serial' and
                     m.product_id.product_tmpl_id and
                     m.product_id.product_tmpl_id.sn_product_type
        )
        
        _logger.info(f'[WIZARD] Filtered to {len(serial_moves)} serial moves with SN type')
        
        if not serial_moves:
            raise UserError(_(
                '❌ No products with SN tracking!\n\n'
                'Transfer: %s\n'
                'Total products: %s\n\n'
                'Requirements:\n'
                '✓ Tracking = "By Unique Serial Number"\n'
                '✓ SN Product Type (M/W) configured'
            ) % (picking.name, len(all_moves)))
        
        # ==========================================
        # Build lines with STRICT validation
        # ==========================================
        lines = []
        errors = []
        
        for move in serial_moves:
            # CRITICAL: Validate move.id is a real integer
            if not move.id:
                errors.append(f'{move.product_id.display_name}: move.id is False')
                _logger.error(f'[WIZARD] move.id is False for {move}')
                continue
            
            if isinstance(move.id, models.NewId):
                errors.append(f'{move.product_id.display_name}: move.id is NewId')
                _logger.error(f'[WIZARD] move.id is NewId: {move.id}')
                continue
            
            if not isinstance(move.id, int):
                errors.append(f'{move.product_id.display_name}: move.id type is {type(move.id)}')
                _logger.error(f'[WIZARD] move.id has wrong type: {type(move.id)}')
                continue
            
            # Verify move can be loaded
            try:
                test_move = self.env['stock.move'].browse(move.id)
                if not test_move.exists():
                    errors.append(f'{move.product_id.display_name}: move does not exist in DB')
                    _logger.error(f'[WIZARD] move.id {move.id} does not exist')
                    continue
            except Exception as e:
                errors.append(f'{move.product_id.display_name}: cannot browse move')
                _logger.error(f'[WIZARD] Cannot browse move {move.id}: {str(e)}')
                continue
            
            qty = int(move.product_uom_qty)
            if qty <= 0:
                _logger.info(f'[WIZARD] Skipping {move.product_id.display_name} - qty=0')
                continue
            
            sn_type = move.product_id.product_tmpl_id.sn_product_type
            
            line_vals = {
                'move_id': move.id,  # Real integer ID
                'product_id': move.product_id.id,
                'product_name': move.product_id.display_name,
                'quantity_in_picking': qty,
                'quantity_existing': 0,
                'quantity': qty,
                'sn_type': sn_type,
                'generate': True,
            }
            
            lines.append((0, 0, line_vals))
            
            _logger.info(f'[WIZARD] ✓ Added: {move.product_id.display_name}, move_id={move.id} (type={type(move.id)}), qty={qty}')
        
        # Report errors if any
        if errors and not lines:
            error_msg = '\n'.join(errors)
            raise UserError(_(
                '❌ Cannot create wizard lines!\n\n'
                'Errors:\n%s\n\n'
                'This usually means moves are not properly saved.\n'
                'Please try:\n'
                '1. Refresh the page\n'
                '2. Click "Mark as Todo" again\n'
                '3. Contact support if issue persists'
            ) % error_msg)
        
        if not lines:
            raise UserError(_(
                '❌ No products to generate!\n\n'
                'Found %s products with SN tracking,\n'
                'but all have qty=0 or other issues.'
            ) % len(serial_moves))
        
        res['line_ids'] = lines
        
        _logger.info(f'[WIZARD] ✅ Ready with {len(lines)} lines')
        
        if errors:
            _logger.warning(f'[WIZARD] Had errors but created {len(lines)} lines:\n' + '\n'.join(errors))
        
        return res
    
    def action_generate_and_close(self):
        """Generate serial numbers WITHOUT creating move lines"""
        self.ensure_one()
        
        if not self.can_generate:
            raise UserError(_('No products selected for generation!'))
        
        if self.picking_id.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_('Transfer state changed!'))
        
        StockLot = self.env['stock.lot']
        total_generated = 0
        generated_details = []
        errors = []
        
        for line in self.line_ids.filtered(lambda l: l.generate and l.quantity > 0):
            try:
                # Validate move
                if not line.move_id or not line.move_id.exists():
                    raise ValidationError(_('Stock move no longer exists!'))
                
                if line.move_id.picking_id != self.picking_id:
                    raise ValidationError(_('Move does not belong to this transfer!'))
                
                actual_qty = line.quantity
                
                # Generate serial numbers ONLY
                serial_numbers = StockLot.generate_serial_numbers(
                    line.product_id.product_tmpl_id.id,
                    line.product_id.id,
                    line.sn_type,
                    actual_qty,
                    picking_id=self.picking_id.id
                )
                
                _logger.info(f'Generated {len(serial_numbers)} SNs for {line.product_name}')
                
                # DO NOT CREATE stock.move.line
                
                total_generated += len(serial_numbers)
                
                generated_details.append(
                    f"✓ {line.product_name}: {len(serial_numbers)} SNs (Type: {line.sn_type})"
                )
                
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
                '✅ Generated %s serial numbers!\n\n'
                '%s\n\n'
                '📝 SNs created but NOT assigned yet\n'
                '▶️ Next: Scan SNs to assign them'
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
    
    wizard_id = fields.Many2one(
        'brodher.stock.picking.sn.wizard',
        required=True,
        ondelete='cascade'
    )
    
    move_id = fields.Many2one(
        'stock.move',
        string='Move',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    product_name = fields.Char('Product Name', readonly=True)
    
    quantity_in_picking = fields.Integer('Qty in Transfer', readonly=True)
    quantity_existing = fields.Integer('Already Assigned', readonly=True)
    quantity = fields.Integer('Qty to Generate', required=True, default=1)
    
    sn_type = fields.Selection([
        ('M', 'Man'),
        ('W', 'Woman')
    ], string='SN Type', required=True, default='M')
    
    generate = fields.Boolean('Generate?', default=True)
    preview_sn = fields.Char('Preview', compute='_compute_preview_sn')
    
    @api.depends('sn_type', 'quantity')
    def _compute_preview_sn(self):
        for line in self:
            if line.sn_type and line.quantity > 0:
                try:
                    year = datetime.now().strftime('%y')
                    StockLot = self.env['stock.lot']
                    
                    next_seq = StockLot._get_next_sequence_global(line.sn_type, year)
                    preview = f"PF{year}{line.sn_type}{next_seq:07d}"
                    
                    if line.quantity > 1:
                        last_seq = next_seq + line.quantity - 1
                        preview += f" ... PF{year}{line.sn_type}{last_seq:07d}"
                    
                    line.preview_sn = preview
                except:
                    line.preview_sn = 'Preview not available'
            else:
                line.preview_sn = ''