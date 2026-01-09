# -*- coding: utf-8 -*-
from odoo import models, fields

class MessageWizard(models.TransientModel):
    _name = 'brodher.message.wizard'
    _description = 'Message Wizard'
    
    message = fields.Text(string='Message', readonly=True)