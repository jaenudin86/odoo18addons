# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    sn_move_ids = fields.One2many('brodher.sn.move', 'picking_id', string='SN Moves')
    scanned_sn_count = fields.Integer(string='Scanned SN', compute='_compute_scanned_sn_count')
    require_sn_scan = fields.Boolean(string='Require SN', compute='_compute_require_sn_scan')
    has_sn_products = fields.Boolean(string='Has SN Products', compute='_compute_has_sn_products')
    
    @api.depends('sn_move_ids')
    def _compute_scanned_sn_count(self):
        for picking in self:
            picking.scanned_sn_count = len(picking.sn_move_ids)
    
    @api.depends('move_ids_without_package')
    def _compute_require_sn_scan(self):
        """Check if picking requires SN scan - ONLY for products with SN tracking"""
        for picking in self:
            picking.require_sn_scan = any(
                move.product_id.tracking == 'serial' and 
                move.product_id.product_tmpl_id.sn_product_type
                for move in picking.move_ids_without_package
            )
    
    @api.depends('move_ids_without_package')
    def _compute_has_sn_products(self):
        """Check if picking has products with SN tracking"""
        for picking in self:
            picking.has_sn_products = any(
                move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type
                for move in picking.move_ids_without_package
            )
    
    def action_scan_serial_number(self):
        self.ensure_one()
        
        # Check if has SN products
        if not self.has_sn_products:
            raise UserError(_(
                'This picking does not contain any products with Serial Number tracking!\n\n'
                'Please ensure products have:\n'
                '1. Tracking: By Unique Serial Number\n'
                '2. Serial Number Type: Man or Woman'
            ))
        
        move_type = 'internal'
        if self.picking_type_code == 'incoming':
            move_type = 'in'
        elif self.picking_type_code == 'outgoing':
            move_type = 'out'
        
        return {
            'name': _('Scan Serial Number - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_move_type': move_type,
                'default_location_src_id': self.location_id.id,
                'default_location_dest_id': self.location_dest_id.id,
            }
        }
    
    def action_view_sn_moves(self):
        self.ensure_one()
        return {
            'name': _('Serial Number Moves - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.sn.move',
            'view_mode': 'tree,form',
            'domain': [('picking_id', '=', self.id)],
        }
    

    
    def _check_sn_scan_completion(self):
        """Check if all required SNs are scanned - ONLY for products with SN tracking"""
        self.ensure_one()
        
        # Check if there are ANY products that require SN
        has_sn_products = False
        
        for move in self.move_ids_without_package:
            product_tmpl = move.product_id.product_tmpl_id
            
            # Check if product has SN tracking enabled
            if move.product_id.tracking == 'serial' and product_tmpl.sn_product_type:
                has_sn_products = True
                
                # Count scanned SN for this product
                scanned_count = len(self.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id.product_id.product_tmpl_id == product_tmpl
                ))
                required_qty = int(move.product_uom_qty)
                
                # Check if not enough scanned
                if scanned_count < required_qty:
                    return False, _(
                        'Product "%s" requires %d serial numbers, but only %d scanned!\n\n'
                        '⚠️ Please scan all serial numbers for products with SN tracking.'
                    ) % (product_tmpl.name, required_qty, scanned_count)
        
        # If no SN products at all, or all scanned - return True
        return True, None
    def action_sync_sn_to_move_lines(self):
        """Sync scanned SNs to stock move lines - FIXED for outgoing"""
        self.ensure_one()
        
        _logger.info('=== Syncing SN to Move Lines for Picking %s ===' % self.name)
        
        for sn_move in self.sn_move_ids:
            sn = sn_move.serial_number_id
            
            # Find stock move
            stock_move = self.move_ids_without_package.filtered(
                lambda m: m.product_id == sn.product_id
            )
            
            if not stock_move:
                _logger.warning('Stock move not found for product %s' % sn.product_id.name)
                continue
            
            stock_move = stock_move[0]
            
            # Check if move line exists for this SN
            move_line = self.env['stock.move.line'].search([
                ('picking_id', '=', self.id),
                ('move_id', '=', stock_move.id),
                ('lot_id', '=', sn.id)
            ], limit=1)
            
            if not move_line:
                # Get correct locations from sn_move
                loc_src = sn_move.location_src_id
                loc_dest = sn_move.location_dest_id
                
                # Fallback to picking locations if not set
                if not loc_src:
                    loc_src = self.location_id
                if not loc_dest:
                    loc_dest = self.location_dest_id
                
                _logger.info('Creating move line: %s → %s' % (loc_src.complete_name, loc_dest.complete_name))
                
                # Create move line
                move_line_vals = {
                    'picking_id': self.id,
                    'move_id': stock_move.id,
                    'product_id': sn.product_id.id,
                    'product_uom_id': sn.product_id.uom_id.id,
                    'location_id': loc_src.id,
                    'location_dest_id': loc_dest.id,
                    'lot_id': sn.id,
                    'lot_name': sn.name,
                    'quantity': 1,
                    'qty_done': 1,
                    'company_id': self.env.company.id,
                }
                
                new_move_line = self.env['stock.move.line'].create(move_line_vals)
                _logger.info('✓ Created move line ID %s for SN %s' % (new_move_line.id, sn.name))
                
            else:
                # Update qty_done if not set
                if move_line.qty_done == 0:
                    move_line.write({'qty_done': 1})
                    _logger.info('✓ Updated qty_done for existing move line')
        
        # Recompute stock moves
        for move in self.move_ids_without_package:
            move._action_assign()
            move._recompute_state()
        
        _logger.info('=== Sync completed ===')
        
        return True
    def action_assign(self):
        """Override assign - sync SN to move lines after assign"""
        res = super(StockPicking, self).action_assign()
        
        # Sync scanned SNs to move lines
        for picking in self:
            if picking.has_sn_products and picking.sn_move_ids:
                picking.action_sync_sn_to_move_lines()
        
        return res
    def button_validate(self):
        """Override validate - only check SN for products with SN tracking"""
        for picking in self:
            # Check if ANY product requires SN
            has_sn_products = any(
                move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type
                for move in picking.move_ids_without_package
            )
            
            # Only check SN completion if there are SN products
            if has_sn_products:
                is_complete, error_msg = picking._check_sn_scan_completion()
                
                if not is_complete:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'brodher.sn.validation.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_picking_id': picking.id,
                            'default_warning_message': error_msg,
                        }
                    }
        
        # Continue with normal validation
        return super(StockPicking, self).button_validate()