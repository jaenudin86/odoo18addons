# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class BrodherConfirmValidateWizard(models.TransientModel):
    _name = 'brodher.confirm.validate.wizard'
    _description = 'Konfirmasi Validasi Penerimaan'

    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True, readonly=True)
    message = fields.Text(string='Pesan', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        # Call the original button_validate with skip_confirmation context
        return self.picking_id.with_context(skip_incoming_confirmation=True).button_validate()
