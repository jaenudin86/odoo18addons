from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class StockBatchInputWizard(models.TransientModel):
    _name = 'stock.batch.input.wizard'
    _description = 'Wizard Input Batch Number & Expired Date'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Receipt',
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        'stock.batch.input.wizard.line',
        'wizard_id',
        string='Lines',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        picking_id = self.env.context.get('active_id')
        if not picking_id:
            return res

        picking = self.env['stock.picking'].browse(picking_id)

        if picking.picking_type_code != 'incoming':
            raise UserError(_('Wizard ini hanya untuk penerimaan barang (Receipt).'))

        lines = []
        # Group per produk — 1 baris per produk, bukan per SN
        seen_products = set()
        for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            product = move.product_id
            if product.tracking not in ('lot', 'serial'):
                continue
            if product.id in seen_products:
                continue
            seen_products.add(product.id)

            # Ambil batch & expired dari SN pertama kalau sudah ada
            first_lot = move.move_line_ids.mapped('lot_id')[:1]
            lines.append((0, 0, {
                'move_id': move.id,
                'product_id': product.id,
                'product_uom_id': move.product_uom.id,
                'sn_count': len(move.move_line_ids),
                'x_batch_number': first_lot.x_batch_number if first_lot else False,
                'expiration_date': first_lot.expiration_date if first_lot else False,
            }))

        res['picking_id'] = picking_id
        res['line_ids'] = lines
        return res

    def action_confirm(self):
        """Apply batch number & expired date ke semua SN per produk."""
        self.ensure_one()

        # Validasi semua line harus terisi
        for line in self.line_ids:
            if not line.x_batch_number:
                raise ValidationError(_(
                    'Batch number wajib diisi untuk produk: %s'
                ) % line.product_id.display_name)
            if not line.expiration_date:
                raise ValidationError(_(
                    'Expired date wajib diisi untuk produk: %s'
                ) % line.product_id.display_name)

        for line in self.line_ids:
            move = line.move_id
            # Apply ke semua lot/SN yang ada di move line produk ini
            lots = move.move_line_ids.mapped('lot_id')
            lots.write({
                'x_batch_number': line.x_batch_number,
                'expiration_date': line.expiration_date,
            })

        return {'type': 'ir.actions.act_window_close'}


class StockBatchInputWizardLine(models.TransientModel):
    _name = 'stock.batch.input.wizard.line'
    _description = 'Line Wizard Input Batch & Expiry'

    wizard_id = fields.Many2one(
        'stock.batch.input.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Move',
        required=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Produk',
        required=True,
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        readonly=True,
    )
    sn_count = fields.Integer(
        string='Jumlah SN',
        readonly=True,
    )
    x_batch_number = fields.Char(
        string='Batch Number',
        required=True,
    )
    expiration_date = fields.Datetime(
        string='Expired Date',
        required=True,
    )
