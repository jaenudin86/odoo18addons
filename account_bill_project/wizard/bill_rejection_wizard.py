# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class BillRejectionWizard(models.TransientModel):
    _name = 'bill.rejection.wizard'
    _description = 'Wizard Penolakan Tagihan'

    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Tagihan',
        required=True,
    )
    rejection_note = fields.Text(
        string='Alasan Penolakan',
        required=True,
    )

    def action_confirm_reject(self):
        self.ensure_one()
        move = self.move_id
        if move.x_approval_state != 'waiting':
            raise UserError(_('Tagihan tidak dalam status menunggu persetujuan.'))

        move.write({
            'x_approval_state': 'rejected',
            'x_rejected_reason': self.rejection_note,
        })
        move._log_approval('rejected', _('Ditolak oleh %s. Alasan: %s') % (
            self.env.user.name, self.rejection_note
        ))
        return {'type': 'ir.actions.act_window_close'}
