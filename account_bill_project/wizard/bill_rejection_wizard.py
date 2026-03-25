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
        if move.x_approval_state not in ('waiting_manager', 'waiting_director'):
            raise UserError(_('Tagihan tidak dalam status menunggu persetujuan.'))

        move.write({
            'x_approval_state': 'rejected',
            'x_approval_note': self.rejection_note,
        })
        move.message_post(
            body=_('<b>Tagihan Ditolak</b><br/>Alasan: %s') % self.rejection_note,
            message_type='notification',
        )

        # Log
        self.env['account.bill.approval.log'].create({
            'move_id': move.id,
            'action': 'reject',
            'note': self.rejection_note,
        })

        return {'type': 'ir.actions.act_window_close'}
