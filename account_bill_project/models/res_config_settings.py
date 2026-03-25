# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Approval Users ───────────────────────────────────────────────────────
    bill_approval_manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Finance Manager (Approver)',
        domain="[('share', '=', False)]",
        config_parameter='account_bill_project.approval_manager_id',
        help='User ini akan menerima notifikasi dan dapat menyetujui tagihan.',
    )
    bill_approval_director_id = fields.Many2one(
        comodel_name='res.users',
        string='Direktur Keuangan (Approver)',
        domain="[('share', '=', False)]",
        config_parameter='account_bill_project.approval_director_id',
        help='User ini diperlukan untuk tagihan di atas batas nilai tertentu.',
    )

    # ── Limit Direktur ───────────────────────────────────────────────────────
    bill_director_approval_limit = fields.Float(
        string='Batas Nilai — Perlu Direktur (Rp)',
        default=50000000,
        config_parameter='account_bill_project.director_approval_limit',
        help='Tagihan dengan total >= nilai ini memerlukan persetujuan Direktur.',
    )
