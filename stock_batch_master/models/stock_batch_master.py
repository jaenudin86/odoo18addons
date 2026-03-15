from odoo import models, fields


class StockBatchMaster(models.Model):
    _name = 'stock.batch.master'
    _description = 'Batch Number Master'
    _order = 'name'

    name = fields.Char(
        string='Batch Number',
        required=True,
        copy=False,
        index=True,
    )
    description = fields.Text(
        string='Description',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    lot_ids = fields.One2many(
        comodel_name='stock.lot',
        inverse_name='batch_master_id',
        string='Serial/Lot Numbers',
        readonly=True,
    )
    lot_count = fields.Integer(
        string='SN/Lot Count',
        compute='_compute_lot_count',
    )

    def _compute_lot_count(self):
        for rec in self:
            rec.lot_count = len(rec.lot_ids)

    def action_view_lots(self):
        self.ensure_one()
        return {
            'name': 'Serial/Lot Numbers',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('batch_master_id', '=', self.id)],
            'context': {'default_batch_master_id': self.id},
        }
