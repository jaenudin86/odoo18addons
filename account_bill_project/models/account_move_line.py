# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # ── Buat product tidak wajib di invoice line ──────────────────────────────
    # Di Odoo 18 vendor bills, product_id tidak wajib secara default,
    # tapi kita pastikan account_id (COA) yang jadi field utama.

    @api.onchange('account_id')
    def _onchange_account_sync_analytic(self):
        """
        Saat account COA dipilih di baris, sync analytic dari header
        jika header sudah diisi.
        """
        move = self.move_id
        if move and move.x_analytic_account_id:
            pct = move.x_analytic_distribution_pct or 100.0
            self.analytic_distribution = {
                str(move.x_analytic_account_id.id): pct
            }

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Setelah create, sync analytic dari header
        for line in lines:
            move = line.move_id
            if (
                move
                and move.x_analytic_account_id
                and line.display_type == 'product'
            ):
                pct = move.x_analytic_distribution_pct or 100.0
                line.analytic_distribution = {
                    str(move.x_analytic_account_id.id): pct
                }
        return lines
