from odoo import models, fields


class StockLot(models.Model):
    _inherit = 'stock.lot'

    batch_master_id = fields.Many2one(
        comodel_name='stock.batch.master',
        string='Batch Number',
        index=True,
        tracking=True,
        help='Batch number that this serial/lot number belongs to.',
    )
