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
            raise UserError(_('No picking specified!'))
        
        picking = self.env['stock.picking'].browse(picking_id)
        
        if not picking.exists():
            raise UserError(_('Transfer not found!'))
        
        if picking.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_(
                'Cannot generate serial numbers!\n\n'
                'Transfer "%s" is in state: %s\n\n'
                'Please click "Mark as Todo" or "Check Availability" first.'
            ) % (picking.name, picking.state))
        
        _logger.info(f'Opening Generate SN wizard for picking: {picking.name}')
        
        moves = picking.move_ids_without_package or picking.move_ids
        
        if not moves:
            raise UserError(_('No stock moves found in transfer "%s"!') % picking.name)
        
        serial_moves = moves.filtered(
            lambda m: m.product_id and 
                     m.product_id.tracking == 'serial' and 
                     m.product_id.product_tmpl_id.sn_product_type
        )
        
        if not serial_moves:
            raise UserError(_('No products with Serial Number tracking found!'))
        
        lines = []
        for move in serial_moves:
            if not move.product_id or not move.product_id.product_tmpl_id:
                continue
            
            qty_needed = int(move.product_uom_qty)
            qty_existing = len(move.move_line_ids.filtered(lambda ml: ml.lot_id))
            qty_to_generate = max(0, qty_needed - qty_existing)
            
            if qty_to_generate > 0:
                product_tmpl = move.product_id.product_tmpl_id
                sn_type = product_tmpl.sn_product_type or 'M'
                
                lines.append((0, 0, {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.display_name,
                    'quantity_in_picking': qty_needed,
                    'quantity_existing': qty_existing,
                    'quantity': qty_to_generate,
                    'sn_type': sn_type,
                    'generate': True,
                }))
        
        if not lines:
            raise UserError(_('All products already have serial numbers!'))
        
        res['line_ids'] = lines
        return res
    
    def action_generate_and_close(self):
        """Generate serial numbers WITHOUT creating move lines"""
        self.ensure_one()
        
        if not self.can_generate:
            raise UserError(_('No products selected for generation!'))
        
        if self.picking_id.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_('Transfer state has changed. Cannot generate.'))
        
        StockLot = self.env['stock.lot']
        total_generated = 0
        generated_details = []
        errors = []
        
        for line in self.line_ids.filtered(lambda l: l.generate and l.quantity > 0):
            try:
                if not line.move_id or not line.move_id.exists():
                    raise ValidationError(_('Stock move no longer exists!'))
                
                if line.move_id.picking_id != self.picking_id:
                    raise ValidationError(_('Move does not belong to this picking!'))
                
                actual_qty = line.quantity
                
                # Generate serial numbers ONLY (no move lines)
                serial_numbers = StockLot.generate_serial_numbers(
                    line.product_id.product_tmpl_id.id,
                    line.product_id.id,
                    line.sn_type,
                    actual_qty,
                    picking_id=self.picking_id.id
                )
                
                _logger.info(f'Generated {len(serial_numbers)} SNs for {line.product_name}')
                
                # ========== CRITICAL ==========
                # DO NOT CREATE stock.move.line here
                # Only create stock.lot records
                # Move lines created during SCAN
                # ==============================
                
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
                'Successfully generated %s serial numbers!\n\n%s\n\n'
                '⚠️ IMPORTANT: Serial numbers created but NOT assigned yet.\n'
                '✓ Next: SCAN these serial numbers.\n'
                '✓ Final: VALIDATE after all scanned.'
            ) % (total_generated, details_message)
            msg_type = 'success'
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