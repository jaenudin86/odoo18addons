from odoo import fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    x_batch_number = fields.Char(
        string='Batch Number',
        index=True,
    )

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    x_batch_number = fields.Char(
        related='lot_id.x_batch_number',
        string='Batch Number',
        store=True,
        readonly=True
    )
    
    expiration_date = fields.Datetime(
        related='lot_id.expiration_date',
        string='Expiration Date',
        store=True,
        readonly=True
    )
