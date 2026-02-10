# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Field untuk handle user access di Settings page
    # Ini related ke pos.config yang dipilih di header
    pos_user_access_ids = fields.Many2many(
        related='pos_config_id.user_access_ids',
        readonly=False,
        string='POS User Access'
    )
