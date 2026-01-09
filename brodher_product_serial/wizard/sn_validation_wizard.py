# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SNValidationWizard(models.TransientModel):
    _name = 'brodher.sn.validation.wizard'
    _description = 'SN Validation Warning'
    
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True)
    warning_message = fields.Text(string='Warning', readonly=True)
    
    def action_continue_scan(self):
        return self.picking_id.action_scan_serial_number()
    
    def action_force_validate(self):
        return super(type(self.picking_id), self.picking_id).button_validate()