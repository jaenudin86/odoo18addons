# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountBillApprovalLog(models.Model):
    """Log historis approval per tagihan."""
    _name = 'account.bill.approval.log'
    _description = 'Log Approval Vendor Bill'
    _order = 'create_date desc'

    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Tagihan',
        required=True,
        ondelete='cascade',
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Approver',
        required=True,
        default=lambda self: self.env.user,
    )

    action = fields.Selection(
        selection=[
            ('submit', 'Diajukan'),
            ('approve_manager', 'Disetujui Manager'),
            ('approve_director', 'Disetujui Direktur'),
            ('reject', 'Ditolak'),
            ('reset', 'Reset ke Draft'),
        ],
        string='Aksi',
        required=True,
    )

    note = fields.Text(string='Catatan')

    date = fields.Datetime(
        string='Tanggal',
        default=fields.Datetime.now,
    )
