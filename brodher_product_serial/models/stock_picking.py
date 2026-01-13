# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # ========== EXISTING SCAN FIELDS (TIDAK DIUBAH) ==========
    sn_move_ids = fields.One2many('brodher.sn.move', 'picking_id', string='SN Moves')
    scanned_sn_count = fields.Integer(string='Scanned SN', compute='_compute_scanned_sn_count')
    require_sn_scan = fields.Boolean(string='Require SN', compute='_compute_require_sn_scan')
    has_sn_products = fields.Boolean(string='Has SN Products', compute='_compute_has_sn_products')
    
    # ========== NEW GENERATION FIELDS ==========
    serial_numbers_generated = fields.Boolean(
        'Serial Numbers Generated', 
        default=False,
        help="Flag to track if SN generation button has been clicked"
    )
    
    generated_sn_count = fields.Integer(
        'Generated SNs', 
        compute='_compute_generated_sn_count',
        help="How many SNs should be available (based on expected qty)"
    )
    
    sn_remaining = fields.Integer(
        'Remaining SNs to Scan',
        compute='_compute_sn_remaining',
        help="How many SNs still need to be scanned"
    )
    
    sn_scan_complete = fields.Boolean(
        'All SNs Scanned',
        compute='_compute_sn_remaining',
        help="True if all generated SNs have been scanned"
    )
    
    # ========== EXISTING COMPUTES (TIDAK DIUBAH) ==========
    @api.depends('sn_move_ids')
    def _compute_scanned_sn_count(self):
        for picking in self:
            picking.scanned_sn_count = len(picking.sn_move_ids)
    
    @api.depends('move_ids_without_package')
    def _compute_require_sn_scan(self):
        for picking in self:
            picking.require_sn_scan = any(
                move.product_id.tracking == 'serial' and 
                move.product_id.product_tmpl_id.sn_product_type
                for move in picking.move_ids_without_package
            )
    
    @api.depends('move_ids_without_package')
    def _compute_has_sn_products(self):
        for picking in self:
            picking.has_sn_products = any(
                move.product_id.tracking == 'serial' and 
                move.product_id.product_tmpl_id.sn_product_type
                for move in picking.move_ids_without_package
            )
    
    # ========== NEW COMPUTES (SIMPLE FLAG-BASED) ==========
    @api.depends('move_ids_without_package', 'serial_numbers_generated')
    def _compute_generated_sn_count(self):
        """
        Count expected SNs based on flag and product qty.
        Simple and fast - no database query needed.
        """
        for picking in self:
            if picking.serial_numbers_generated and picking.has_sn_products:
                # Sum all qty for products that need SN
                total = sum(picking.move_ids_without_package.filtered(
                    lambda m: m.product_id.tracking == 'serial' and 
                             m.product_id.product_tmpl_id.sn_product_type
                ).mapped('product_uom_qty'))
                picking.generated_sn_count = int(total)
            else:
                picking.generated_sn_count = 0
    
    @api.depends('generated_sn_count', 'scanned_sn_count')
    def _compute_sn_remaining(self):
        """Calculate remaining SNs to scan"""
        for picking in self:
            remaining = picking.generated_sn_count - picking.scanned_sn_count
            picking.sn_remaining = max(0, remaining)
            picking.sn_scan_complete = (
                remaining <= 0 and 
                picking.generated_sn_count > 0
            )
    
    # ========== ACTIONS ==========
    def action_generate_serial_numbers(self):
        """Open wizard to generate serial numbers"""
        self.ensure_one()
        
        if self.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_('Picking must be in Confirmed/Ready state!'))
        
        if not self.has_sn_products:
            raise UserError(_('No products with serial tracking!'))
        
        return {
            'name': _('Generate Serial Numbers - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.stock.picking.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
            }
        }
    
    def action_bulk_generate_all(self):
        """Quick generate all SNs automatically"""
        self.ensure_one()
        
        if self.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_('Picking must be in Confirmed/Ready state!'))
        
        StockLot = self.env['stock.lot']
        total_generated = 0
        
        for move in self.move_ids_without_package.filtered(
            lambda m: m.product_id.tracking == 'serial' and 
                     m.product_id.product_tmpl_id.sn_product_type
        ):
            qty = int(move.product_uom_qty)
            if qty <= 0:
                continue
            
            sn_type = move.product_id.product_tmpl_id.sn_product_type or 'M'
            
            # Generate SNs (no move lines)
            serial_numbers = StockLot.generate_serial_numbers(
                move.product_id.product_tmpl_id.id,
                move.product_id.id,
                sn_type,
                qty,
                picking_id=self.id
            )
            
            total_generated += len(serial_numbers)
        
        if total_generated > 0:
            self.serial_numbers_generated = True
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Generated %s serial numbers!') % total_generated,
                'type': 'success',
                'sticky': True,
            }
        }
    
    def action_view_generated_sns(self):
        """View generated SNs"""
        self.ensure_one()
        
        # Get products
        product_ids = self.move_ids_without_package.filtered(
            lambda m: m.product_id.tracking == 'serial' and 
                     m.product_id.product_tmpl_id.sn_product_type
        ).mapped('product_id').ids
        
        # Get recent lots
        lots = self.env['stock.lot'].search([
            ('product_id', 'in', product_ids),
            ('create_date', '>=', self.create_date)
        ])
        
        return {
            'name': _('Generated Serial Numbers'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', lots.ids)],
        }
    
    # ========== EXISTING SCAN ACTIONS (TIDAK DIUBAH) ==========
    def action_scan_serial_number(self):
        self.ensure_one()
        
        if not self.has_sn_products:
            raise UserError(_('No products with serial tracking!'))
        
        if self.picking_type_code == 'incoming':
            wizard_model = 'brodher.scan.sn.in.wizard'
        elif self.picking_type_code == 'outgoing':
            wizard_model = 'brodher.scan.sn.out.wizard'
        else:
            wizard_model = 'brodher.scan.sn.in.wizard'
        
        return {
            'name': _('Scan Serial Number'),
            'type': 'ir.actions.act_window',
            'res_model': wizard_model,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
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
    
    # ========== EXISTING VALIDATION (TIDAK DIUBAH) ==========
    def _check_sn_scan_completion(self):
        self.ensure_one()
        
        for move in self.move_ids_without_package:
            product_tmpl = move.product_id.product_tmpl_id
            
            if move.product_id.tracking == 'serial' and product_tmpl.sn_product_type:
                scanned_count = len(self.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id.product_id.product_tmpl_id == product_tmpl
                ))
                required_qty = int(move.product_uom_qty)
                
                if scanned_count < required_qty:
                    return False, _(
                        'Product "%s" requires %d serial numbers, but only %d scanned!'
                    ) % (product_tmpl.name, required_qty, scanned_count)
        
        return True, None
    
    def button_validate(self):
        for picking in self:
            if picking.has_sn_products:
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
        
        return super(StockPicking, self).button_validate()


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    sn_needed = fields.Integer('SN Needed', compute='_compute_sn_status')
    sn_scanned = fields.Integer('SN Scanned', compute='_compute_sn_status')
    sn_status = fields.Char('SN Status', compute='_compute_sn_status')
    
    @api.depends('product_uom_qty', 'picking_id.sn_move_ids')
    def _compute_sn_status(self):
        for move in self:
            if move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type:
                move.sn_needed = int(move.product_uom_qty)
                
                if move.picking_id:
                    move.sn_scanned = len(move.picking_id.sn_move_ids.filtered(
                        lambda sm: sm.serial_number_id.product_id.product_tmpl_id == move.product_id.product_tmpl_id
                    ))
                else:
                    move.sn_scanned = 0
                
                if move.sn_scanned >= move.sn_needed:
                    move.sn_status = '✓ Complete'
                elif move.sn_scanned > 0:
                    move.sn_status = f'⚠ {move.sn_scanned}/{move.sn_needed}'
                else:
                    move.sn_status = '✗ Not Scanned'
            else:
                move.sn_needed = 0
                move.sn_scanned = 0
                move.sn_status = 'N/A'