# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Analytic Header ──────────────────────────────────────────────────────
    x_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account (Project)',
        tracking=True,
        help='Analytic account header — otomatis berlaku untuk semua baris.',
    )
    x_analytic_distribution_pct = fields.Float(
        string='% Alokasi',
        default=100.0,
        digits=(5, 2),
    )

    # ── Approval ─────────────────────────────────────────────────────────────
    x_approval_state = fields.Selection(
        selection=[
            ('draft',    'Draft'),
            ('waiting',  'Menunggu Persetujuan'),
            ('approved', 'Disetujui'),
            ('rejected', 'Ditolak'),
        ],
        string='Status Persetujuan',
        default='draft',
        tracking=True,
        copy=False,
    )
    x_approved_by = fields.Many2one(
        'res.users', string='Disetujui Oleh', readonly=True, copy=False, tracking=True,
    )
    x_approved_date = fields.Datetime(
        string='Tanggal Disetujui', readonly=True, copy=False,
    )
    x_rejected_reason = fields.Text(
        string='Alasan Penolakan', readonly=True, copy=False,
    )
    x_approval_ids = fields.One2many(
        'account.bill.approval', 'move_id', string='Log Persetujuan', copy=False,
    )
    x_require_director_approval = fields.Boolean(
        string='Perlu Persetujuan Direktur',
        compute='_compute_require_director',
        store=True,
    )

    # ── Compute ──────────────────────────────────────────────────────────────

    @api.depends('amount_total', 'move_type')
    def _compute_require_director(self):
        limit = float(self.env['ir.config_parameter'].sudo().get_param(
            'account_bill_project.director_approval_limit', default='50000000'
        ))
        for move in self:
            move.x_require_director_approval = (
                move.move_type == 'in_invoice' and move.amount_total > limit
            )

    # ── Onchange: sync analytic → semua baris ────────────────────────────────

    @api.onchange('x_analytic_account_id', 'x_analytic_distribution_pct')
    def _onchange_analytic_header(self):
        self._sync_analytic_to_lines()

    def _sync_analytic_to_lines(self):
        """Propagate analytic header ke setiap invoice line."""
        for move in self:
            if not move.x_analytic_account_id:
                # Jika header dikosongkan, hapus analytic di semua baris
                for line in move.invoice_line_ids:
                    line.analytic_distribution = {}
                continue
            pct = move.x_analytic_distribution_pct or 100.0
            distribution = {str(move.x_analytic_account_id.id): pct}
            for line in move.invoice_line_ids:
                line.analytic_distribution = distribution

    # ── Override action_post ─────────────────────────────────────────────────

    def action_post(self):
        for move in self:
            if move.move_type == 'in_invoice':
                if move.x_approval_state == 'waiting':
                    raise UserError(_(
                        'Tagihan "%s" masih menunggu persetujuan.\n'
                        'Silakan minta approval terlebih dahulu.'
                    ) % move.name)
                if move.x_approval_state == 'rejected':
                    raise UserError(_(
                        'Tagihan "%s" telah ditolak.\n'
                        'Reset ke draft dan perbaiki sebelum melanjutkan.'
                    ) % move.name)
                # Sync analytic sebelum posting
                move._sync_analytic_to_lines()
        return super().action_post()

    # ── Approval Actions ─────────────────────────────────────────────────────

    def action_submit_for_approval(self):
        for move in self:
            if move.move_type != 'in_invoice':
                continue
            if not move.invoice_line_ids:
                raise UserError(_('Tambahkan minimal satu baris sebelum mengajukan persetujuan.'))
            move.x_approval_state = 'waiting'
            move._log_approval('waiting', _('Diajukan untuk persetujuan oleh %s.') % self.env.user.name)
            move._notify_finance_manager()

    def action_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('account_bill_project.group_bill_finance_manager'):
            raise UserError(_('Hanya Finance Manager yang dapat menyetujui tagihan.'))
        self.write({
            'x_approval_state': 'approved',
            'x_approved_by': self.env.user.id,
            'x_approved_date': fields.Datetime.now(),
            'x_rejected_reason': False,
        })
        self._log_approval('approved', _('Disetujui oleh %s.') % self.env.user.name)

    def action_reject(self):
        self.ensure_one()
        if not self.env.user.has_group('account_bill_project.group_bill_finance_manager'):
            raise UserError(_('Hanya Finance Manager yang dapat menolak tagihan.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tolak Tagihan'),
            'res_model': 'bill.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }

    def action_reset_to_draft_custom(self):
        for move in self:
            move.write({
                'x_approval_state': 'draft',
                'x_approved_by': False,
                'x_approved_date': False,
                'x_rejected_reason': False,
            })
        return self.button_draft()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _log_approval(self, state, note):
        self.env['account.bill.approval'].create({
            'move_id': self.id,
            'user_id': self.env.user.id,
            'state': state,
            'note': note,
        })
        self.message_post(body=note, message_type='notification')

    def _notify_finance_manager(self):
        group = self.env.ref(
            'account_bill_project.group_bill_finance_manager', raise_if_not_found=False
        )
        if not group:
            return
        partner_ids = group.users.mapped('partner_id').ids
        if partner_ids:
            self.message_post(
                body=_('Tagihan <b>%s</b> dari <b>%s</b> menunggu persetujuan Anda.') % (
                    self.name, self.partner_id.name or '-',
                ),
                partner_ids=partner_ids,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
