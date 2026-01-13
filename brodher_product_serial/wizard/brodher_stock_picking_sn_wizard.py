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
        """
        SIMPLIFIED: Do NOT create lines here
        Just set picking_id
        """
        res = super(BrodherStockPickingSNWizard, self).default_get(fields_list)
        
        picking_id = self.env.context.get('default_picking_id') or self.env.context.get('active_id')
        
        if picking_id:
            res['picking_id'] = picking_id
        
        # DO NOT set line_ids here - it causes the error
        
        return res
    
    @api.model
    def create(self, vals):
        """
        Override create to populate lines AFTER wizard is created
        """
        # Create wizard first WITHOUT lines
        wizard = super(BrodherStockPickingSNWizard, self).create(vals)
        
        # Now populate lines
        wizard._populate_lines()
        
        return wizard
    
    def _populate_lines(self):
        """
        Populate wizard lines after wizard is created
        This avoids the NewId issue
        """
        self.ensure_one()
        
        if not self.picking_id:
            raise UserError(_('No picking specified!'))
        
        _logger.info(f'[WIZARD] Populating lines for: {self.picking_id.name}')
        
        # Get moves
        moves = self.env['stock.move'].search([
            ('picking_id', '=', self.picking_id.id),
            ('state', 'not in', ['cancel', 'done']),
            ('product_id', '!=', False),
            ('product_id.tracking', '=', 'serial'),
        ])
        
        _logger.info(f'[WIZARD] Found {len(moves)} serial moves')
        
        if not moves:
            raise UserError(_(
                'No products with serial tracking found!\n\n'
                'Transfer: %s'
            ) % self.picking_id.name)
        
        # Create lines one by one
        line_ids = []
        
        for move in moves:
            # Validate move.id
            if not move.id or not isinstance(move.id, int):
                _logger.warning(f'[WIZARD] Skipping invalid move: {move}')
                continue
            
            qty = int(move.product_uom_qty)
            if qty <= 0:
                continue
            
            # Get SN type
            sn_type = 'M'
            if move.product_id.product_tmpl_id:
                sn_type = getattr(move.product_id.product_tmpl_id, 'sn_product_type', None) or 'M'
            
            # Create line directly
            line = self.env['brodher.stock.picking.sn.wizard.line'].create({
                'wizard_id': self.id,  # Wizard already exists
                'move_id': move.id,    # Real integer ID
                'product_id': move.product_id.id,
                'product_name': move.product_id.display_name,
                'quantity_in_picking': qty,
                'quantity_existing': 0,
                'quantity': qty,
                'sn_type': sn_type,
                'generate': True,
            })
            
            line_ids.append(line.id)
            
            _logger.info(f'[WIZARD] Created line: {move.product_id.display_name}, move_id={move.id}')
        
        if not line_ids:
            raise UserError(_('No products to generate!'))
        
        _logger.info(f'[WIZARD] Created {len(line_ids)} lines')
    
    def action_generate_and_close(self):
        """Generate serial numbers"""
        self.ensure_one()
        
        if not self.can_generate:
            raise UserError(_('No products selected!'))
        
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
                
                total_generated += len(serial_numbers)
                
                generated_details.append(
                    f"✓ {line.product_name}: {len(serial_numbers)} SNs"
                )
                
                first_sn = serial_numbers[0].name
                last_sn = serial_numbers[-1].name if len(serial_numbers) > 1 else first_sn
                
                if len(serial_numbers) > 1:
                    generated_details.append(f"   {first_sn} ... {last_sn}")
                
            except Exception as e:
                errors.append(f"✗ {line.product_name}: {str(e)}")
        
        if total_generated > 0:
            self.picking_id.serial_numbers_generated = True
        
        details = '\n'.join(generated_details)
        if errors:
            details += '\n\nErrors:\n' + '\n'.join(errors)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Generated %s SNs!\n\n%s') % (total_generated, details),
                'type': 'success' if total_generated > 0 else 'warning',
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