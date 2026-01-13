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
        res = super(BrodherStockPickingSNWizard, self).default_get(fields_list)
        
        picking_id = self.env.context.get('default_picking_id')
        if not picking_id:
            raise UserError(_('No picking specified!'))
        
        picking = self.env['stock.picking'].browse(picking_id)
        
        if not picking.exists():
            raise UserError(_('Picking not found!'))
        
        lines = []
        for move in picking.move_ids_without_package.filtered(
            lambda m: m.product_id.tracking == 'serial' and m.product_id.product_tmpl_id.sn_product_type
        ):
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
            raise UserError(_(
                'All products in this transfer already have serial numbers assigned!\n\n'
                'No serial numbers need to be generated.'
            ))
        
        res['line_ids'] = lines
        return res
    
    def action_generate_and_close(self):
        self.ensure_one()
        
        if not self.can_generate:
            raise UserError(_('No products selected for generation!'))
        
        if self.picking_id.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_('Transfer state has changed. Please refresh and try again.'))
        
        StockLot = self.env['stock.lot']
        total_generated = 0
        generated_details = []
        errors = []
        
        for line in self.line_ids.filtered(lambda l: l.generate and l.quantity > 0):
            try:
                if line.move_id.picking_id != self.picking_id:
                    raise ValidationError(_('Move does not belong to this picking!'))
                
                qty_needed = int(line.move_id.product_uom_qty)
                qty_existing = len(line.move_id.move_line_ids.filtered(lambda ml: ml.lot_id))
                qty_to_generate = max(0, qty_needed - qty_existing)
                
                if qty_to_generate <= 0:
                    generated_details.append(
                        f"⊘ {line.product_name}: Already complete ({qty_existing}/{qty_needed})"
                    )
                    continue
                
                actual_qty = min(line.quantity, qty_to_generate)
                
                serial_numbers = StockLot.generate_serial_numbers(
                    line.product_id.product_tmpl_id.id,
                    line.product_id.id,
                    line.sn_type,
                    actual_qty,
                    picking_id=self.picking_id.id
                )
                
                _logger.info(f'Generated {len(serial_numbers)} SNs for {line.product_name} in picking {self.picking_id.name}')
                
                for sn in serial_numbers:
                    self.env['stock.move.line'].create({
                        'move_id': line.move_id.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_id.uom_id.id,
                        'location_id': self.picking_id.location_id.id,
                        'location_dest_id': self.picking_id.location_dest_id.id,
                        'picking_id': self.picking_id.id,
                        'lot_id': sn.id,
                        'quantity': 1,
                    })
                    total_generated += 1
                
                generated_details.append(
                    f"✓ {line.product_name}: {actual_qty} SNs generated (Type: {line.sn_type})"
                )
                
                first_sn = serial_numbers[0].name
                last_sn = serial_numbers[-1].name if len(serial_numbers) > 1 else first_sn
                
                if len(serial_numbers) > 1:
                    generated_details.append(f"   Range: {first_sn} ... {last_sn}")
                else:
                    generated_details.append(f"   SN: {first_sn}")
                
            except Exception as e:
                error_msg = str(e)
                _logger.error(f'Error generating SNs for {line.product_name}: {error_msg}', exc_info=True)
                errors.append(f"✗ {line.product_name}: {error_msg}")
        
        if total_generated > 0:
            self.picking_id.serial_numbers_generated = True
        
        details_message = '\n'.join(generated_details)
        
        if errors:
            details_message += '\n\nErrors:\n' + '\n'.join(errors)
        
        if total_generated > 0:
            message = _(
                'Successfully generated %s serial numbers!\n\n%s\n\n'
                '✓ You can now proceed to scan these serial numbers.'
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
    move_id = fields.Many2one('stock.move', string='Move', required=True, readonly=True)
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
                except Exception as e:
                    line.preview_sn = 'Preview not available'
            else:
                line.preview_sn = ''
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_('Quantity cannot be negative!'))
            
            max_qty = line.quantity_in_picking - line.quantity_existing
            if line.quantity > max_qty:
                raise ValidationError(_(
                    'Cannot generate more than %s serial numbers for %s!'
                ) % (max_qty, line.product_name))