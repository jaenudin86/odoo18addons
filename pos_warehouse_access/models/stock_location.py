# -*- coding: utf-8 -*-

from odoo import models


class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    # No method override - rely on record rules only
