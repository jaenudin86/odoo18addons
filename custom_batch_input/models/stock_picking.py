from odoo import models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_open_batch_input_wizard(self):
        """Buka wizard input batch number & expired date."""
        self.ensure_one()
        return {
            'name': _('Input Batch & Expired Date'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.batch.input.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'stock.picking',
            },
        }

    def button_validate(self):
        """Blokir validate kalau batch number / expired date belum diisi."""
        for picking in self:
            if picking.picking_type_code != 'incoming':
                continue
            if picking.state in ('done', 'cancel'):
                continue

            missing = []
            for move in picking.move_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
            ):
                if move.product_id.tracking not in ('lot', 'serial'):
                    continue

                for ml in move.move_line_ids:
                    if not ml.lot_id:
                        missing.append(
                            _('• %s — serial number belum diisi')
                            % move.product_id.display_name
                        )
                    elif not ml.lot_id.x_batch_number:
                        missing.append(
                            _('• %s (SN: %s) — batch number belum diisi')
                            % (move.product_id.display_name, ml.lot_id.name)
                        )
                    elif not ml.lot_id.expiration_date:
                        missing.append(
                            _('• %s (SN: %s) — expired date belum diisi')
                            % (move.product_id.display_name, ml.lot_id.name)
                        )

            if missing:
                raise UserError(
                    _('Tidak dapat memvalidasi penerimaan!\n\n'
                      'Produk berikut belum lengkap:\n\n%s\n\n'
                      'Silakan klik tombol "Input Batch & Expired" terlebih dahulu.')
                    % '\n'.join(missing)
                )

        return super().button_validate()
