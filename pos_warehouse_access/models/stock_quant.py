# -*- coding: utf-8 -*-

from odoo import models


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    # No method override - rely on record rules only
