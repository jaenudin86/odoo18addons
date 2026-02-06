# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SNPrintWizard(models.TransientModel):
    _name = 'brodher.sn.print.wizard'
    _description = 'Print Serial Number QR Wizard'
    
    picking_id = fields.Many2one('stock.picking', 'Transfer', required=True, readonly=True)
    picking_name = fields.Char('Transfer', related='picking_id.name')
    
    step = fields.Selection([
        ('product', 'Select Product'),
        ('serial', 'Select Serial Numbers'),
    ], default='product', required=True)
    
    # Step 1: Product selection
    product_line_ids = fields.One2many(
        'brodher.sn.print.wizard.product', 
        'wizard_id', 
        'Products'
    )
    
    # Step 2: Serial number selection
    sn_line_ids = fields.One2many(
        'brodher.sn.print.wizard.line', 
        'wizard_id', 
        'Serial Numbers'
    )
    
    total_products_selected = fields.Integer('Produk Dipilih', compute='_compute_totals')
    total_sn_selected = fields.Integer('SN Dipilih', compute='_compute_totals')
    
    @api.depends('product_line_ids.selected', 'sn_line_ids.selected')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_products_selected = len(wizard.product_line_ids.filtered('selected'))
            wizard.total_sn_selected = len(wizard.sn_line_ids.filtered('selected'))
    
    @api.model
    def default_get(self, fields_list):
        """Step 1: Populate products"""
        res = super(SNPrintWizard, self).default_get(fields_list)
        
        picking_id = self.env.context.get('default_picking_id')
        if not picking_id:
            return res
        
        picking = self.env['stock.picking'].browse(picking_id)
        
        # Get products with SN
        products = picking.move_ids_without_package.filtered(
            lambda m: m.product_id.tracking == 'serial' and 
                     m.product_id.product_tmpl_id.sn_product_type
        ).mapped('product_id')
        
        if products:
            lines = []
            for product in products:
                # Count SNs for this product
                sns = self.env['stock.lot'].search([
                    ('product_id', '=', product.id),
                    ('generated_by_picking_id', '=', picking.id)
                ])
                
                printed_count = len(sns.filtered('is_printed'))
                unprinted_count = len(sns.filtered(lambda s: not s.is_printed))
                
                lines.append((0, 0, {
                    'product_id': product.id,
                    'product_name': product.display_name,
                    'total_sn': len(sns),
                    'printed_count': printed_count,
                    'unprinted_count': unprinted_count,
                    'selected': True,  # Default: semua produk dipilih
                }))
            
            res['product_line_ids'] = lines
        
        return res
    
    def action_next_to_serial(self):
        """Step 1 → Step 2: Load SNs for selected products"""
        self.ensure_one()
        
        selected_products = self.product_line_ids.filtered('selected')
        
        if not selected_products:
            raise UserError(_('Pilih minimal 1 produk!'))
        
        # Load serial numbers for selected products
        sn_lines = []
        for product_line in selected_products:
            sns = self.env['stock.lot'].search([
                ('product_id', '=', product_line.product_id.id),
                ('generated_by_picking_id', '=', self.picking_id.id)
            ], order='name')
            
            for sn in sns:
                sn_lines.append((0, 0, {
                    'serial_number_id': sn.id,
                    'serial_number_name': sn.name,
                    'product_id': sn.product_id.id,
                    'product_name': sn.product_id.display_name,
                    'sn_type': sn.sn_type,
                    'is_printed': sn.is_printed,
                    'print_count': sn.print_count,
                    'last_print_date': sn.last_print_date,
                    'selected': not sn.is_printed,  # Default: pilih yang belum dicetak
                }))
        
        self.write({
            'step': 'serial',
            'sn_line_ids': [(5, 0, 0)] + sn_lines,  # Clear then add
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.sn.print.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_back_to_product(self):
        """Step 2 → Step 1: Back to product selection"""
        self.ensure_one()
        self.step = 'product'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.sn.print.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_print_selected(self):
        """Print selected serial numbers"""
        self.ensure_one()
        
        selected_lines = self.sn_line_ids.filtered('selected')
        
        if not selected_lines:
            raise UserError(_('Tidak ada SN yang dipilih!\n\nSilakan centang SN yang ingin dicetak.'))
        
        selected_sns = selected_lines.mapped('serial_number_id')
        
        # Update print status and create history
        for sn in selected_sns:
            new_count = sn.print_count + 1
            
            sn.write({
                'is_printed': True,
                'print_count': new_count,
                'last_print_date': fields.Datetime.now(),
                'last_print_user': self.env.user.id,
            })
            
            self.env['stock.lot.print.history'].create({
                'lot_id': sn.id,
                'print_date': fields.Datetime.now(),
                'print_user': self.env.user.id,
                'print_count_at_time': new_count,
                'picking_id': self.picking_id.id,
                'notes': f'Cetak dari wizard - Transfer {self.picking_id.name}',
            })
        
        # Generate PDF
        return self.env.ref('brodher_product_serial.action_report_serial_number_qrcode').report_action(selected_sns)
    
    # Quick selection actions for STEP 2
    def action_select_all_sn(self):
        """Select all SNs"""
        self.sn_line_ids.write({'selected': True})
        return {'type': 'ir.actions.do_nothing'}
    
    def action_deselect_all_sn(self):
        """Deselect all SNs"""
        self.sn_line_ids.write({'selected': False})
        return {'type': 'ir.actions.do_nothing'}
    
    def action_select_unprinted(self):
        """Select only unprinted SNs"""
        self.sn_line_ids.write({'selected': False})
        self.sn_line_ids.filtered(lambda l: not l.is_printed).write({'selected': True})
        return {'type': 'ir.actions.do_nothing'}
    
    def action_select_by_product(self):
        """Select by product"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Select by Product',
            'res_model': 'brodher.sn.print.product.select',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wizard_id': self.id},
        }


class SNPrintWizardProduct(models.TransientModel):
    _name = 'brodher.sn.print.wizard.product'
    _description = 'Print Wizard - Product Selection'
    
    wizard_id = fields.Many2one('brodher.sn.print.wizard', required=True, ondelete='cascade')
    
    product_id = fields.Many2one('product.product', 'Product', required=True, readonly=True)
    product_name = fields.Char('Nama Produk', readonly=True)
    
    total_sn = fields.Integer('Total SN', readonly=True)
    printed_count = fields.Integer('Sudah Dicetak', readonly=True)
    unprinted_count = fields.Integer('Belum Dicetak', readonly=True)
    
    selected = fields.Boolean('Pilih', default=True)


class SNPrintWizardLine(models.TransientModel):
    _name = 'brodher.sn.print.wizard.line'
    _description = 'Print Wizard - Serial Number Selection'
    
    wizard_id = fields.Many2one('brodher.sn.print.wizard', required=True, ondelete='cascade')
    
    serial_number_id = fields.Many2one('stock.lot', 'Serial Number', required=True, readonly=True)
    serial_number_name = fields.Char('SN', readonly=True)
    
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_name = fields.Char('Nama Produk', readonly=True)
    sn_type = fields.Selection([('M', 'Man'), ('W', 'Woman')], 'Type', readonly=True)
    
    is_printed = fields.Boolean('Sudah Dicetak?', readonly=True)
    print_count = fields.Integer('Cetak Ke-', readonly=True)
    last_print_date = fields.Datetime('Terakhir Dicetak', readonly=True)
    
    selected = fields.Boolean('Pilih', default=True)