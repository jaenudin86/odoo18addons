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
            """Override default_get to populate lines"""
            res = super(BrodherStockPickingSNWizard, self).default_get(fields_list)
            
            picking_id = self.env.context.get('default_picking_id') or self.env.context.get('active_id')
            
            if not picking_id:
                raise UserError(_('No transfer specified! Please open this wizard from a receipt.'))
            
            picking = self.env['stock.picking'].browse(picking_id)
            
            if not picking.exists():
                raise UserError(_('Transfer not found!'))
            
            # CRITICAL: Check picking state
            if picking.state not in ['confirmed', 'assigned', 'waiting']:
                raise UserError(_(
                    'Cannot generate serial numbers!\n\n'
                    'Transfer "%s" is in state: %s\n\n'
                    'Please click "Check Availability" or "Mark as Todo" first.'
                ) % (picking.name, picking.state))
            
            _logger.info(f'Opening Generate SN wizard for: {picking.name} (state: {picking.state})')
            
            # Get moves - try both fields
            moves = picking.move_ids_without_package
            if not moves:
                moves = picking.move_ids
            
            if not moves:
                raise UserError(_(
                    'No stock moves found!\n\n'
                    'Transfer: %s\n'
                    'State: %s\n\n'
                    'Please ensure products are added and transfer is confirmed.'
                ) % (picking.name, picking.state))
            
            _logger.info(f'Found {len(moves)} moves in picking')
            
            # Filter serial products
            serial_moves = moves.filtered(
                lambda m: m.product_id and 
                        m.product_id.tracking == 'serial' and 
                        m.product_id.product_tmpl_id and
                        m.product_id.product_tmpl_id.sn_product_type
            )
            
            if not serial_moves:
                raise UserError(_(
                    'No products with serial tracking found!\n\n'
                    'Total products: %s\n\n'
                    'Please check:\n'
                    '1. Products have tracking = "By Unique Serial Number"\n'
                    '2. Products have SN Product Type (M/W) configured'
                ) % len(moves))
            
            _logger.info(f'Found {len(serial_moves)} moves with serial tracking')
            
            # Build lines
            lines = []
            for move in serial_moves:
                # Validate move has product
                if not move.product_id:
                    _logger.warning(f'Skipping move {move.id} - no product')
                    continue
                
                if not move.product_id.product_tmpl_id:
                    _logger.warning(f'Skipping move {move.id} - no product template')
                    continue
                
                # CRITICAL: Ensure move.id exists and is valid
                if not move.id or isinstance(move.id, models.NewId):
                    _logger.error(f'Move has invalid ID: {move.id}')
                    continue
                
                qty_needed = int(move.product_uom_qty)
                
                if qty_needed <= 0:
                    continue
                
                product_tmpl = move.product_id.product_tmpl_id
                sn_type = product_tmpl.sn_product_type or 'M'
                
                line_vals = {
                    'move_id': move.id,  # CRITICAL - must be real ID
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.display_name,
                    'quantity_in_picking': qty_needed,
                    'quantity_existing': 0,  # Always 0 since we don't create move_line
                    'quantity': qty_needed,
                    'sn_type': sn_type,
                    'generate': True,
                }
                
                lines.append((0, 0, line_vals))
                _logger.info(f'Added line for move {move.id}: {move.product_id.display_name}')
            
            if not lines:
                raise UserError(_(
                    'No products to generate!\n\n'
                    'All products either:\n'
                    '- Already have SNs, or\n'
                    '- Have quantity = 0'
                ))
            
            res['line_ids'] = lines
            _logger.info(f'Wizard ready with {len(lines)} lines')
            
            return res
        def action_generate_and_close(self):
            """Generate serial numbers WITHOUT creating move lines"""
            self.ensure_one()
            
            if not self.can_generate:
                raise UserError(_('No products selected!'))
            
            if self.picking_id.state not in ['confirmed', 'assigned', 'waiting']:
                raise UserError(_('Transfer state has changed!'))
            
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
                    
                    # ========== DO NOT CREATE move_line ==========
                    # Only create stock.lot
                    # Move lines created during SCAN
                    # =============================================
                    
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
                    _logger.error(f'Error: {error_msg}', exc_info=True)
                    errors.append(f"✗ {line.product_name}: {error_msg}")
            
            if total_generated > 0:
                self.picking_id.serial_numbers_generated = True
            
            details_message = '\n'.join(generated_details)
            
            if errors:
                details_message += '\n\nErrors:\n' + '\n'.join(errors)
            
            if total_generated > 0:
                message = _(
                    'Successfully generated %s serial numbers!\n\n%s\n\n'
                    '⚠️ IMPORTANT:\n'
                    '1. Serial numbers are created in system\n'
                    '2. NOT yet assigned to transfer\n'
                    '3. Quantity in Detailed Operations = 0\n'
                    '\n'
                    '✓ Next: SCAN these SNs to assign them\n'
                    '✓ Final: VALIDATE after all scanned'
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
    move_id = fields.Many2one('stock.move', string='Move', required=True, readonly=True, ondelete='cascade')
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
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_('Quantity cannot be negative!'))
            if line.quantity > 1000:
                raise ValidationError(_('Cannot generate more than 1000 SNs at once!'))