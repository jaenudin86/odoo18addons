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
        """Override default_get - ONLY show products with serial tracking AND sn_product_type"""
        res = super(BrodherStockPickingSNWizard, self).default_get(fields_list)
        
        picking_id = self.env.context.get('default_picking_id') or self.env.context.get('active_id')
        
        if not picking_id:
            raise UserError(_('No transfer ID provided!'))
        
        picking = self.env['stock.picking'].browse(picking_id)
        
        if not picking.exists():
            raise UserError(_('Transfer not found!'))
        
        _logger.info(f'[WIZARD] Opening for: {picking.name}, state: {picking.state}')
        
        # ============================================
        # CRITICAL FILTER: ONLY serial + sn_product_type
        # ============================================
        all_moves = self.env['stock.move'].search([
            ('picking_id', '=', picking.id),
            ('product_id', '!=', False),
            ('product_id.tracking', '=', 'serial'),  # Must have serial tracking
            ('product_id.product_tmpl_id.sn_product_type', '!=', False),  # Must have SN type (M/W)
        ])
        
        _logger.info(f'[WIZARD] Found {len(all_moves)} products with serial tracking + SN type')
        
        # Debug: Log all moves in picking
        all_picking_moves = picking.move_ids
        _logger.info(f'[WIZARD] Total moves in picking: {len(all_picking_moves)}')
        
        for move in all_picking_moves:
            tracking = move.product_id.tracking if move.product_id else 'N/A'
            sn_type = move.product_id.product_tmpl_id.sn_product_type if move.product_id and move.product_id.product_tmpl_id else None
            _logger.info(f'  - {move.product_id.display_name if move.product_id else "NO PRODUCT"}: tracking={tracking}, sn_type={sn_type}')
        
        if not all_moves:
            raise UserError(_(
                '❌ No products with SN tracking found!\n\n'
                'Transfer: %s\n'
                'Total products: %s\n\n'
                'Requirements for SN generation:\n'
                '✓ Product tracking = "By Unique Serial Number"\n'
                '✓ Product has SN Type (M/W) configured\n\n'
                'Please check product configuration in:\n'
                'Product → General Information Tab'
            ) % (picking.name, len(all_picking_moves)))
        
        # Build lines
        lines = []
        
        for move in all_moves:
            # Validate move ID
            if not move.id or isinstance(move.id, models.NewId):
                _logger.warning(f'[WIZARD] Skipping NewId move')
                continue
            
            qty = int(move.product_uom_qty)
            if qty <= 0:
                _logger.info(f'[WIZARD] Skipping {move.product_id.display_name} - qty=0')
                continue
            
            # Get SN type (guaranteed to exist due to filter)
            sn_type = move.product_id.product_tmpl_id.sn_product_type
            
            lines.append((0, 0, {
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_name': move.product_id.display_name,
                'quantity_in_picking': qty,
                'quantity_existing': 0,
                'quantity': qty,
                'sn_type': sn_type,
                'generate': True,
            }))
            
            _logger.info(f'[WIZARD] ✓ Added: {move.product_id.display_name}, type={sn_type}, qty={qty}')
        
        if not lines:
            raise UserError(_(
                '❌ No products to generate!\n\n'
                'Found %s products with SN tracking, but:\n'
                '• All have quantity = 0, or\n'
                '• Already have SNs generated\n\n'
                'Please check product quantities.'
            ) % len(all_moves))
        
        res['line_ids'] = lines
        
        _logger.info(f'[WIZARD] ✅ Ready with {len(lines)} lines')
        
        return res
    def action_generate_and_close(self):
        """Generate serial numbers WITHOUT creating move lines"""
        self.ensure_one()
        
        if not self.can_generate:
            raise UserError(_('No products selected for generation!'))
        
        if self.picking_id.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_(
                'Transfer state changed to "%s".\n'
                'Cannot generate in this state.'
            ) % self.picking_id.state)
        
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
                '✅ Successfully generated %s serial numbers!\n\n'
                '%s\n\n'
                '📝 IMPORTANT:\n'
                '• SNs created in system\n'
                '• NOT assigned to operations yet\n'
                '• Detailed Operations qty = 0\n'
                '\n'
                '▶️ NEXT: Scan SNs to assign them\n'
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
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    move_id = fields.Many2one(
        'stock.move',
        string='Move',
        required=True,
        readonly=True,
        ondelete='cascade',
        help="Stock move from the transfer - MUST be a saved record with real ID"
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
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_('Quantity cannot be negative!'))
            if line.quantity > 10000:
                raise ValidationError(_('Cannot generate more than 10,000 SNs at once!'))