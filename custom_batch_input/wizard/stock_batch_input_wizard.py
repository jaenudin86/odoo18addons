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

        # Hanya untuk receipt (incoming)
        if picking.picking_type_code != 'incoming':
            raise UserError(_('Wizard ini hanya bisa digunakan untuk penerimaan barang (Receipt).'))

        lines = []
        for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            product = move.product_id
            # Hanya produk yang tracking-nya lot/serial
            if product.tracking not in ('lot', 'serial'):
                continue

            # Cek apakah sudah ada lot di move line
            existing_lots = move.move_line_ids.mapped('lot_id')
            if existing_lots:
                for lot in existing_lots:
                    move_line = move.move_line_ids.filtered(lambda l: l.lot_id == lot)
                    lines.append((0, 0, {
                        'move_id': move.id,
                        'product_id': product.id,
                        'product_uom_id': move.product_uom.id,
                        'qty_done': sum(move_line.mapped('quantity')),
                        'lot_id': lot.id,
                        'expiration_date': lot.expiration_date,
                        'lot_name': lot.name,
                    }))
            else:
                lines.append((0, 0, {
                    'move_id': move.id,
                    'product_id': product.id,
                    'product_uom_id': move.product_uom.id,
                    'qty_done': move.product_uom_qty,
                    'lot_id': False,
                    'expiration_date': False,
                    'lot_name': False,
                }))

        res['picking_id'] = picking_id
        res['line_ids'] = lines
        return res

    def action_confirm(self):
        """Simpan batch number & expired date ke stock.move.line"""
        self.ensure_one()

        # Validasi semua line harus terisi
        for line in self.line_ids:
            if not line.lot_name:
                raise ValidationError(_(
                    'Batch number wajib diisi untuk produk: %s'
                ) % line.product_id.display_name)
            if not line.expiration_date:
                raise ValidationError(_(
                    'Expired date wajib diisi untuk produk: %s'
                ) % line.product_id.display_name)

        for line in self.line_ids:
            # Cari atau buat lot baru
            lot = self.env['stock.lot'].search([
                ('name', '=', line.lot_name),
                ('product_id', '=', line.product_id.id),
                ('company_id', '=', self.picking_id.company_id.id),
            ], limit=1)

            if not lot:
                lot = self.env['stock.lot'].create({
                    'name': line.lot_name,
                    'product_id': line.product_id.id,
                    'expiration_date': line.expiration_date,
                    'company_id': self.picking_id.company_id.id,
                })
            else:
                # Update expiry kalau lot sudah ada
                lot.expiration_date = line.expiration_date

            # Update atau buat move line
            move = line.move_id
            existing_move_line = move.move_line_ids.filtered(
                lambda l: l.lot_id == lot or not l.lot_id
            )

            if existing_move_line:
                existing_move_line[0].write({
                    'lot_id': lot.id,
                    'quantity': line.qty_done,
                })
                # Hapus duplikat kalau ada
                if len(existing_move_line) > 1:
                    existing_move_line[1:].unlink()
            else:
                self.env['stock.move.line'].create({
                    'move_id': move.id,
                    'picking_id': self.picking_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.qty_done,
                    'lot_id': lot.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
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
    qty_done = fields.Float(
        string='Qty',
        digits='Product Unit of Measure',
        required=True,
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch Number (Existing)',
        domain="[('product_id', '=', product_id)]",
    )
    lot_name = fields.Char(
        string='Batch Number',
        required=True,
    )
    expiration_date = fields.Datetime(
        string='Expired Date',
        required=True,
    )

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """Auto-fill batch name & expiry dari lot yang dipilih"""
        if self.lot_id:
            self.lot_name = self.lot_id.name
            self.expiration_date = self.lot_id.expiration_date
