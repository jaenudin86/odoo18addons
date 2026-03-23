from odoo import models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """Override validate: wajib batch number & expired date untuk semua produk
        yang memiliki tracking 'lot' pada penerimaan barang (Receipt)."""

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

                # Cek apakah semua move lines sudah punya lot
                if not move.move_line_ids:
                    missing.append(
                        _('• %s — belum ada batch number') % move.product_id.display_name
                    )
                    continue

                for ml in move.move_line_ids:
                    if not ml.lot_id:
                        missing.append(
                            _('• %s — batch number belum diisi') % move.product_id.display_name
                        )
                    elif not ml.lot_id.expiration_date:
                        missing.append(
                            _('• %s (Batch: %s) — expired date belum diisi')
                            % (move.product_id.display_name, ml.lot_id.name)
                        )

            if missing:
                raise UserError(
                    _('Tidak dapat memvalidasi penerimaan!\n\n'
                      'Produk berikut belum lengkap batch number / expired date:\n\n%s\n\n'
                      'Silakan klik tombol "🏷️ Input Batch & Expired" terlebih dahulu.')
                    % '\n'.join(missing)
                )

        return super().button_validate()
