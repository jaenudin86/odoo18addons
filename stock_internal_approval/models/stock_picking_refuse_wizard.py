# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class StockPickingRefuseWizard(models.TransientModel):
    _name = 'stock.picking.refuse.wizard'
    _description = 'Refuse Internal Transfer Wizard'

    picking_ids = fields.Many2many(
        'stock.picking',
        string='Transfers',
    )

    refused_reason = fields.Text(
        string='Refusal Reason',
        required=True,
    )

    def action_refuse(self):
        if not self.refused_reason:
            raise UserError(_('Please provide a reason for refusing the transfer.'))

        for picking in self.picking_ids:
            picking.write({
                'approval_state': 'refused',
                'refused_by': self.env.uid,
                'refused_reason': self.refused_reason,
                'approved_by': False,
                'approved_date': False,
            })
            picking.message_post(
                body=_('Transfer refused by %s.\nReason: %s') % (
                    self.env.user.name, self.refused_reason
                ),
                message_type='notification',
            )

        return {'type': 'ir.actions.act_window_close'}
