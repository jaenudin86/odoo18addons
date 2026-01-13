# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # ========== EXISTING FIELDS (SCAN SN) ==========
    sn_move_ids = fields.One2many('brodher.sn.move', 'picking_id', string='SN Moves')
    scanned_sn_count = fields.Integer(string='Scanned SN', compute='_compute_scanned_sn_count')
    require_sn_scan = fields.Boolean(string='Require SN', compute='_compute_require_sn_scan')
    has_sn_products = fields.Boolean(string='Has SN Products', compute='_compute_has_sn_products')
    
    # ========== NEW FIELDS (GENERATE SN) ==========
    serial_numbers_generated = fields.Boolean('Serial Numbers Generated', default=False)
    generated_sn_count = fields.Integer('Generated SNs', compute='_compute_generated_sn_count', store=True)
    sn_generation_summary = fields.Text('SN Generation Summary', compute='_compute_sn_generation_summary')
    
    sn_remaining = fields.Integer(
        'Remaining SNs to Scan',
        compute='_compute_sn_remaining'
    )
    
    sn_scan_complete = fields.Boolean(
        'All SNs Scanned',
        compute='_compute_sn_remaining'
    )
    
    @api.depends('generated_sn_count', 'scanned_sn_count')
    def _compute_sn_remaining(self):
        for picking in self:
            remaining = picking.generated_sn_count - picking.scanned_sn_count
            picking.sn_remaining = max(0, remaining)
            picking.sn_scan_complete = (remaining <= 0 and picking.generated_sn_count > 0)
    # ========== EXISTING COMPUTES (SCAN SN) ==========
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
        """Check if picking has products that NEED SN generation"""
        for picking in self:
            picking.has_sn_products = any(
                move.product_id.tracking == 'serial' and 
                move.product_id.product_tmpl_id.sn_product_type  # Must have SN type
                for move in picking.move_ids_without_package
            )
    
    # ========== NEW COMPUTES (GENERATE SN) ==========
    @api.depends('move_ids_without_package', 'serial_numbers_generated')
    def _compute_generated_sn_count(self):
        """Simple count based on flag and expected qty"""
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
    # @api.depends('move_ids', 'move_line_ids.lot_id')
    # def _compute_sn_generation_summary(self):
    #     """Generate summary of SN status per product"""
    #     for picking in self:
    #         summary_lines = []
            
    #         for move in picking.move_ids_without_package.filtered(
    #             lambda m: m.product_id.tracking == 'serial' and m.product_id.product_tmpl_id.sn_product_type
    #         ):
    #             qty_needed = int(move.product_uom_qty)
    #             qty_ready = len(move.move_line_ids.filtered(lambda ml: ml.lot_id))
                
    #             status = '✓' if qty_ready >= qty_needed else '✗'
    #             summary_lines.append(
    #                 f"{status} {move.product_id.display_name}: {qty_ready}/{qty_needed} SN"
    #             )
            
    #         picking.sn_generation_summary = '\n'.join(summary_lines) if summary_lines else 'No serial products'
    
    # ========== EXISTING ACTIONS (SCAN SN - TIDAK DIUBAH) ==========
    def action_scan_serial_number(self):
        """Open wizard to scan serial number - SPLIT by picking type"""
        self.ensure_one()
        
        # Check if has SN products
        if not self.has_sn_products:
            raise UserError(_(
                'This picking does not contain any products with Serial Number tracking!'
            ))
        
        # Determine wizard based on picking type
        if self.picking_type_code == 'incoming':
            # INCOMING - Barang Masuk
            wizard_model = 'brodher.scan.sn.in.wizard'
            wizard_name = 'Scan Serial Number - INCOMING'
        elif self.picking_type_code == 'outgoing':
            # OUTGOING - Barang Keluar
            wizard_model = 'brodher.scan.sn.out.wizard'
            wizard_name = 'Scan Serial Number - OUTGOING'
        else:
            # INTERNAL - use incoming wizard as default
            wizard_model = 'brodher.scan.sn.in.wizard'
            wizard_name = 'Scan Serial Number - INTERNAL'
        
        return {
            'name': _(wizard_name),
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
        """View scanned SN moves"""
        self.ensure_one()
        return {
            'name': _('Serial Number Moves - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.sn.move',
            'view_mode': 'tree,form',
            'domain': [('picking_id', '=', self.id)],
        }
    
    # ========== NEW ACTIONS (GENERATE SN) ==========
    def action_generate_serial_numbers(self):
        """Open wizard - ONLY for products with serial tracking + SN type"""
        self.ensure_one()
        
        # Validate state
        if self.state == 'draft':
            raise UserError(_(
                '❌ Cannot generate serial numbers!\n\n'
                'Transfer is in DRAFT state.\n\n'
                '📋 Action: Click "Mark as Todo" first'
            ) % self.name)
        
        if self.state not in ['confirmed', 'assigned', 'waiting']:
            raise UserError(_('Transfer must be confirmed! Current state: %s') % self.state)
        
        # ============================================
        # Check if ANY products need SN
        # ============================================
        sn_products = self.move_ids.filtered(
            lambda m: m.product_id and
                    m.product_id.tracking == 'serial' and
                    m.product_id.product_tmpl_id.sn_product_type
        )
        
        if not sn_products:
            # Get stats for error message
            total_products = len(self.move_ids)
            serial_products = len(self.move_ids.filtered(
                lambda m: m.product_id and m.product_id.tracking == 'serial'
            ))
            
            raise UserError(_(
                '❌ No products require SN generation!\n\n'
                'Transfer: %s\n'
                'Total products: %s\n'
                'Products with serial tracking: %s\n'
                'Products with SN Type (M/W): 0\n\n'
                '📋 To use SN generation:\n'
                '1. Go to Product → General Information\n'
                '2. Set Tracking = "By Unique Serial Number"\n'
                '3. Set SN Product Type = M (Man) or W (Woman)'
            ) % (self.name, total_products, serial_products))
        
        _logger.info(f'Opening SN wizard for {self.name}: {len(sn_products)} products need SN')
        
        return {
            'name': _('Generate Serial Numbers - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.stock.picking.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_operation_type': self.picking_type_code,
            }
        }

    def action_bulk_generate_all(self):
            """Quick generate - ONLY for products with serial + SN type"""
            self.ensure_one()
            
            if self.state not in ['confirmed', 'assigned', 'waiting']:
                raise UserError(_('Transfer must be confirmed!'))
            
            StockLot = self.env['stock.lot']
            total_generated = 0
            generated_details = []
            
            # Filter: serial tracking + sn_product_type
            sn_moves = self.move_ids_without_package.filtered(
                lambda m: m.product_id.tracking == 'serial' and
                        m.product_id.product_tmpl_id.sn_product_type
            )
            
            if not sn_moves:
                raise UserError(_(
                    '❌ No products require SN generation!\n\n'
                    'Please ensure products have:\n'
                    '✓ Tracking = "By Unique Serial Number"\n'
                    '✓ SN Product Type (M/W) configured'
                ))
            
            for move in sn_moves:
                qty = int(move.product_uom_qty)
                if qty <= 0:
                    continue
                
                sn_type = move.product_id.product_tmpl_id.sn_product_type
                
                try:
                    serial_numbers = StockLot.generate_serial_numbers(
                        move.product_id.product_tmpl_id.id,
                        move.product_id.id,
                        sn_type,
                        qty,
                        picking_id=self.id
                    )
                    
                    total_generated += len(serial_numbers)
                    generated_details.append(f"✓ {move.product_id.display_name}: {len(serial_numbers)} SNs (Type: {sn_type})")
                    
                except Exception as e:
                    _logger.error(f'Error: {str(e)}')
                    generated_details.append(f"✗ {move.product_id.display_name}: Failed")
            
            if total_generated > 0:
                self.serial_numbers_generated = True
            
            details = '\n'.join(generated_details)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Generated %s SNs!\n\n%s\n\n⚠️ Please SCAN to assign.') % (total_generated, details),
                    'type': 'success',
                    'sticky': True,
                }
            }
    def action_view_generated_sns(self):
        """View all generated serial numbers for this picking"""
        self.ensure_one()
        
        lot_ids = self.move_line_ids.mapped('lot_id').ids
        
        if not lot_ids:
            raise UserError(_('No serial numbers have been generated for this transfer yet.'))
        
        return {
            'name': _('Serial Numbers - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', lot_ids)],
            'context': {
                'default_product_id': False,
                'group_by': 'product_id',
            }
        }
    
    # ========== EXISTING VALIDATION (SCAN SN - TIDAK DIUBAH) ==========
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
    def _get_generated_serial_numbers(self):
        """Get all generated serial numbers for this picking (not yet scanned)"""
        self.ensure_one()
        
        # Get all products in this picking that need SN
        product_ids = self.move_ids_without_package.filtered(
            lambda m: m.product_id.tracking == 'serial' and 
                    m.product_id.product_tmpl_id.sn_product_type
        ).mapped('product_id').ids
        
        if not product_ids:
            return self.env['stock.lot']
        
        # Get serial numbers generated for this picking
        serial_numbers = self.env['stock.lot'].search([
            ('product_id', 'in', product_ids),
            ('generated_by_picking_id', '=', self.id)
        ], order='name asc')
        
        return serial_numbers

    def action_print_sn_qrcode(self):
        """Print QR code labels for generated serial numbers"""
        self.ensure_one()
        
        if not self.serial_numbers_generated:
            raise UserError(_(
                '❌ No serial numbers to print!\n\n'
                'Please generate serial numbers first.'
            ))
        
        serial_numbers = self._get_generated_serial_numbers()
        
        if not serial_numbers:
            raise UserError(_(
                '❌ No serial numbers found!\n\n'
                'Serial numbers may have been generated but not tracked properly.'
            ))
        
        return self.env.ref('brodher_product_serial.action_report_serial_number_qrcode').report_action(self)


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    sn_needed = fields.Integer('SN Needed', compute='_compute_sn_status', store=True)
    sn_generated = fields.Integer('SN Generated', compute='_compute_sn_status', store=True)
    sn_scanned = fields.Integer('SN Scanned', compute='_compute_sn_status', store=True)
    sn_status = fields.Char('SN Status', compute='_compute_sn_status')

    @api.depends('product_uom_qty', 'picking_id.sn_move_ids', 'picking_id.serial_numbers_generated')
    def _compute_sn_status(self):
        for move in self:
            product_tmpl = move.product_id.product_tmpl_id
            
            if move.product_id.tracking == 'serial' and product_tmpl.sn_product_type:
                move.sn_needed = int(move.product_uom_qty)
                
                # Count SCANNED only (no need to check generated)
                if move.picking_id:
                    move.sn_scanned = len(move.picking_id.sn_move_ids.filtered(
                        lambda sm: sm.serial_number_id.product_id.product_tmpl_id == product_tmpl
                    ))
                    
                    # Simple generated check from flag
                    if move.picking_id.serial_numbers_generated:
                        move.sn_generated = move.sn_needed
                    else:
                        move.sn_generated = 0
                else:
                    move.sn_scanned = 0
                    move.sn_generated = 0
                
                # Status
                if move.sn_scanned >= move.sn_needed:
                    move.sn_status = '✓ Complete'
                elif move.sn_generated > 0:
                    if move.sn_scanned > 0:
                        move.sn_status = f'⚠ {move.sn_scanned}/{move.sn_needed}'
                    else:
                        move.sn_status = f'⚠ Generated - Scan Required'
                else:
                    move.sn_status = '✗ Not Generated'
            else:
                move.sn_needed = 0
                move.sn_generated = 0
                move.sn_scanned = 0
                move.sn_status = 'N/A'