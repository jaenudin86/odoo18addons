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
    
    line_ids = fields.One2many(
        'brodher.stock.picking.sn.wizard.line', 
        'wizard_id', 
        string='Products'
    )
    
    # Flag to track if lines have been populated
    lines_populated = fields.Boolean('Lines Populated', default=False)
    
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
    
    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        """
        Populate lines when picking_id is set
        This triggers in form view
        """
        if self.picking_id and not self.lines_populated:
            self._populate_lines_onchange()
            self.lines_populated = True
    
    def _populate_lines_onchange(self):
        """
        Populate wizard lines in onchange context
        """
        if not self.picking_id:
            return
        
        _logger.info(f'[WIZARD ONCHANGE] Populating for: {self.picking_id.name}')
        
        # Get moves via search
        moves = self.env['stock.move'].search([
            ('picking_id', '=', self.picking_id.id),
            ('state', 'not in', ['cancel', 'done']),
            ('product_id', '!=', False),
            ('product_id.tracking', '=', 'serial'),
        ])
        
        _logger.info(f'[WIZARD ONCHANGE] Found {len(moves)} serial moves')
        
        if not moves:
            return
        
        # Build lines as command list (for onchange)
        lines = []
        
        for move in moves:
            if not isinstance(move.id, int):
                continue
            
            qty = int(move.product_uom_qty)
            if qty <= 0:
                continue
            
            # Get SN type
            sn_type = 'M'
            if move.product_id.product_tmpl_id:
                sn_type = getattr(move.product_id.product_tmpl_id, 'sn_product_type', None) or 'M'
            
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
            
            _logger.info(f'[WIZARD ONCHANGE] Added: {move.product_id.display_name}')
        
        if lines:
            self.line_ids = lines
            _logger.info(f'[WIZARD ONCHANGE] Set {len(lines)} lines')
    
    @api.model
    def create(self, vals):
        """
        Override create for when wizard is saved
        """
        wizard = super(BrodherStockPickingSNWizard, self).create(vals)
        
        # If no lines and has picking_id, populate now
        if not wizard.line_ids and wizard.picking_id:
            wizard._populate_lines_create()
        
        return wizard
    
    def _populate_lines_create(self):
        """
        Populate lines after wizard is created (saved to DB)
        """
        self.ensure_one()
        
        if not self.picking_id:
            return
        
        _logger.info(f'[WIZARD CREATE] Populating for: {self.picking_id.name}')
        
        moves = self.env['stock.move'].search([
            ('picking_id', '=', self.picking_id.id),
            ('state', 'not in', ['cancel', 'done']),
            ('product_id', '!=', False),
            ('product_id.tracking', '=', 'serial'),
        ])
        
        _logger.info(f'[WIZARD CREATE] Found {len(moves)} serial moves')
        
        for move in moves:
            if not isinstance(move.id, int):
                continue
            
            qty = int(move.product_uom_qty)
            if qty <= 0:
                continue
            
            sn_type = 'M'
            if move.product_id.product_tmpl_id:
                sn_type = getattr(move.product_id.product_tmpl_id, 'sn_product_type', None) or 'M'
            
            self.env['brodher.stock.picking.sn.wizard.line'].create({
                'wizard_id': self.id,
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_name': move.product_id.display_name,
                'quantity_in_picking': qty,
                'quantity_existing': 0,
                'quantity': qty,
                'sn_type': sn_type,
                'generate': True,
            })
            
            _logger.info(f'[WIZARD CREATE] Created line: {move.product_id.display_name}')
    
    def action_generate_and_close(self):
        """Generate serial numbers"""
        self.ensure_one()
        
        if not self.can_generate:
            raise UserError(_('No products selected for generation!'))
        
        if self.picking_id.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_('Transfer state has changed!'))
        
        StockLot = self.env['stock.lot']
        total_generated = 0
        generated_details = []
        errors = []
        
        for line in self.line_ids.filtered(lambda l: l.generate and l.quantity > 0):
            try:
                serial_numbers = StockLot.generate_serial_numbers(
                    line.product_id.product_tmpl_id.id,
                    line.product_id.id,
                    line.sn_type,
                    line.quantity,
                    picking_id=self.picking_id.id
                )
                
                _logger.info(f'Generated {len(serial_numbers)} SNs for {line.product_name}')
                
                total_generated += len(serial_numbers)
                
                generated_details.append(f"✓ {line.product_name}: {len(serial_numbers)} SNs")
                
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
                '✅ Generated %s serial numbers!\n\n%s\n\n'
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
    
    wizard_id = fields.Many2one('brodher.stock.picking.sn.wizard', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=True, readonly=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    product_name = fields.Char('Product Name', readonly=True)
    
    quantity_in_picking = fields.Integer('Qty in Transfer', readonly=True)
    quantity_existing = fields.Integer('Already Assigned', readonly=True)
    quantity = fields.Integer('Qty to Generate', required=True, default=1)
    
    sn_type = fields.Selection([('M', 'Man'), ('W', 'Woman')], string='SN Type', required=True, default='M')
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