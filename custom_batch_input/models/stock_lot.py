from odoo import fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    x_batch_number = fields.Char(
        string='Batch Number',
        index=True,
    )
