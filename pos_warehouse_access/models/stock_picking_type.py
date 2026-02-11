# -*- coding: utf-8 -*-

from odoo import models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'
    
    # No method override - rely on record rules only
