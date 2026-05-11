# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import io
import zipfile
import base64

_logger = logging.getLogger(__name__)


class SNPrintWizard(models.TransientModel):
    _name = 'brodher.sn.print.wizard'
    _description = 'Print Serial Number QR Wizard'
    
    picking_id = fields.Many2one('stock.picking', 'Transfer', required=True, readonly=True)
    picking_name = fields.Char('Transfer', related='picking_id.name', readonly=True)
    
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
    
    total_sn_selected = fields.Integer('SN Dipilih', compute='_compute_totals')
    batch_size = fields.Integer('SN per File PDF', default=100, required=True) # Reduced default for smoother progress
    
    # Progress tracking
    progress = fields.Float('Progress', default=0.0)
    is_processing = fields.Boolean('Is Processing', default=False)
    current_batch = fields.Integer('Current Batch', default=0)
    total_batches = fields.Integer('Total Batches', default=0)
    processed_pdf_data = fields.Text('Processed PDF Data') # JSON list of attachment IDs
    
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
                    'selected': True,
                }))
            
            res['product_line_ids'] = lines
        
        return res
    
    def action_next_to_serial(self):
        """Step 1 → Step 2: Load SNs for selected products"""
        self.ensure_one()
        
        selected_product_lines = self.product_line_ids.filtered('selected')
        
        if not selected_product_lines:
            raise UserError(_('Pilih minimal 1 produk!'))
        
        selected_products = selected_product_lines.mapped('product_id')
        
        _logger.info(f'[PRINT WIZARD] Loading SNs for {len(selected_products)} products')
        
        # Clear old SN lines if any
        if self.sn_line_ids:
            self.sn_line_ids.unlink()
        
        # Collect all SN data to create
        sn_vals_list = []
        
        for product in selected_products:
            sns = self.env['stock.lot'].search([
                ('product_id', '=', product.id),
                ('generated_by_picking_id', '=', self.picking_id.id)
            ], order='name')
            
            _logger.info(f'[PRINT WIZARD] Found {len(sns)} SNs for {product.display_name}')
            
            for sn in sns:
                sn_vals_list.append((0, 0, {
                    'serial_number_id': sn.id,
                    'serial_number_name': sn.name,
                    'product_id': sn.product_id.id,
                    'product_name': sn.product_id.display_name,
                    'sn_type': sn.sn_type,
                    'is_printed': sn.is_printed,
                    'print_count': sn.print_count,
                    'last_print_date': sn.last_print_date,
                    'selected': not sn.is_printed,
                }))
        
        if not sn_vals_list:
            raise UserError(_('Tidak ada serial number yang ditemukan untuk produk yang dipilih!'))
        
        # Update wizard: ONLY change step and add SN lines
        # DON'T touch product_line_ids!
        self.write({
            'step': 'serial',
            'sn_line_ids': sn_vals_list,
        })
        
        _logger.info(f'[PRINT WIZARD] Created {len(sn_vals_list)} SN lines')
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print QR Code - Pilih Serial Number'),
            'res_model': 'brodher.sn.print.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_back_to_product(self):
        """Step 2 → Step 1: Just change step back"""
        self.ensure_one()
        
        # Just change step back to product
        # Product lines are still there, no need to recreate
        self.step = 'product'
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print QR Code - Pilih Produk'),
            'res_model': 'brodher.sn.print.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_print_selected(self):
        """Entry point for printing - starts the progress bar flow."""
        self.ensure_one()
        selected_lines = self.sn_line_ids.filtered('selected')
        if not selected_lines:
            raise UserError(_('Pilih minimal 1 Serial Number!'))
        
        total_sn = len(selected_lines)
        batch_size = max(1, self.batch_size)
        total_batches = (total_sn + batch_size - 1) // batch_size
        
        self.write({
            'is_processing': True,
            'total_batches': total_batches,
            'current_batch': 0,
            'progress': 0,
            'processed_pdf_data': '[]'
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'sn_print_progress_action',
            'params': {
                'wizard_id': self.id,
            }
        }

    def action_process_next_batch(self):
        """Called by JS or manually to process the next batch."""
        self.ensure_one()
        if not self.is_processing:
            return False
            
        selected_sns = self.sn_line_ids.filtered('selected').mapped('serial_number_id')
        batch_size = self.batch_size
        start = self.current_batch * batch_size
        end = min(start + batch_size, len(selected_sns))
        
        batch_sns = selected_sns[start:end]
        
        # 1. Render PDF for this batch
        report = self.env.ref('brodher_product_serial.action_report_serial_number_qrcode')
        pdf_content, _ = report._render_qweb_pdf(report.id, res_ids=batch_sns.ids)
        
        # Update SN status
        now = fields.Datetime.now()
        for sn in batch_sns:
            new_count = sn.print_count + 1
            sn.write({
                'is_printed': True,
                'print_count': new_count,
                'last_print_date': now,
                'last_print_user': self.env.user.id,
            })
        
        # 2. Save PDF as attachment
        filename = f'batch_{self.current_batch + 1}.pdf'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content).decode(),
            'res_model': self._name,
            'res_id': self.id,
        })
        
        # 3. Update Progress
        import json
        processed_ids = json.loads(self.processed_pdf_data or '[]')
        processed_ids.append(attachment.id)
        
        new_batch = self.current_batch + 1
        progress = (new_batch / self.total_batches) * 100
        
        self.write({
            'current_batch': new_batch,
            'progress': progress,
            'processed_pdf_data': json.dumps(processed_ids)
        })
        
        if new_batch >= self.total_batches:
            return self.action_finalize_printing()
            
        return True

    def action_finalize_printing(self):
        """Combine all batches into one ZIP or return single PDF."""
        import json
        processed_ids = json.loads(self.processed_pdf_data or '[]')
        attachments = self.env['ir.attachment'].browse(processed_ids)
        
        if not attachments:
            return False
            
        if len(attachments) == 1:
            # Single PDF - return it
            self.write({'is_processing': False})
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachments[0].id}?download=true',
                'target': 'self',
            }
            
        # Multiple PDFs - create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, attach in enumerate(attachments):
                filename = f'qr_labels_{self.picking_id.name}_part_{i+1:03d}.pdf'
                zf.writestr(filename, base64.b64decode(attach.datas))
        
        zip_attachment = self.env['ir.attachment'].create({
            'name': f'qr_labels_{self.picking_id.name}.zip',
            'type': 'binary',
            'datas': base64.b64encode(zip_buffer.getvalue()).decode(),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/zip',
        })
        
        self.write({'is_processing': False})
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{zip_attachment.id}?download=true',
            'target': 'self',
        }
    
    # Quick selection actions
    def action_select_all_sn(self):
        self.sn_line_ids.write({'selected': True})
        return self._reload_wizard()
    
    def action_deselect_all_sn(self):
        self.sn_line_ids.write({'selected': False})
        return self._reload_wizard()
    
    def action_select_unprinted(self):
        self.sn_line_ids.write({'selected': False})
        self.sn_line_ids.filtered(lambda l: not l.is_printed).write({'selected': True})
        return self._reload_wizard()
    
    def action_select_printed(self):
        self.sn_line_ids.write({'selected': False})
        self.sn_line_ids.filtered(lambda l: l.is_printed).write({'selected': True})
        return self._reload_wizard()
    
    def _reload_wizard(self):
        """Helper to reload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.sn.print.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class SNPrintWizardProduct(models.TransientModel):
    _name = 'brodher.sn.print.wizard.product'
    _description = 'Print Wizard - Product Selection'
    
    wizard_id = fields.Many2one('brodher.sn.print.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product')  # NOT required, NOT readonly
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