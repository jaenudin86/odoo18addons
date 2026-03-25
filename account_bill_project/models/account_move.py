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
        'res.users', string='Disetujui Oleh',
        readonly=True, copy=False, tracking=True,
    )
    x_approved_date = fields.Datetime(
        string='Tanggal Disetujui', readonly=True, copy=False,
    )
    x_rejected_reason = fields.Text(
        string='Alasan Penolakan', readonly=True, copy=False,
    )
    x_approval_ids = fields.One2many(
        'account.bill.approval.log', 'move_id',
        string='Log Persetujuan', copy=False,
    )
    x_require_director_approval = fields.Boolean(
        string='Perlu Persetujuan Direktur',
        compute='_compute_require_director',
        store=True,
    )

    # ── Override default_get: paksa journal bank/cash untuk vendor bills ─────

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move_type = res.get('move_type') or self._context.get('default_move_type', '')
        if move_type in ('in_invoice', 'in_refund') and 'journal_id' in fields_list:
            journal = self.env['account.journal'].search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', self.env.company.id),
            ], limit=1)
            if journal:
                res['journal_id'] = journal.id
        return res

    # ── Compute ──────────────────────────────────────────────────────────────

    @api.depends('amount_total', 'move_type')
    def _compute_require_director(self):
        limit = float(self.env['ir.config_parameter'].sudo().get_param(
            'account_bill_project.director_approval_limit', default='50000000'
        ))
        for move in self:
            move.x_require_director_approval = (
                move.move_type in ('in_invoice', 'in_refund')
                and move.amount_total > limit
            )

    # ── Onchange: sync analytic header → semua baris ─────────────────────────

    @api.onchange('x_analytic_account_id', 'x_analytic_distribution_pct')
    def _onchange_analytic_header(self):
        self._sync_analytic_to_lines()

    def _sync_analytic_to_lines(self):
        for move in self:
            for line in move.invoice_line_ids:
                if line.display_type != 'product':
                    continue
                if not move.x_analytic_account_id:
                    line.analytic_distribution = {}
                else:
                    pct = move.x_analytic_distribution_pct or 100.0
                    line.analytic_distribution = {
                        str(move.x_analytic_account_id.id): pct
                    }

    def write(self, vals):
        res = super().write(vals)
        if 'x_analytic_account_id' in vals or 'x_analytic_distribution_pct' in vals:
            for move in self:
                if move.move_type in ('in_invoice', 'in_refund'):
                    move._sync_analytic_to_lines()
        return res

    # ── Override action_post ─────────────────────────────────────────────────

    def action_post(self):
        for move in self:
            if move.move_type in ('in_invoice', 'in_refund'):
                if move.x_approval_state == 'waiting':
                    raise UserError(_(
                        'Tagihan "%s" masih menunggu persetujuan.'
                    ) % move.name)
                if move.x_approval_state == 'rejected':
                    raise UserError(_(
                        'Tagihan "%s" telah ditolak. Reset ke draft dulu.'
                    ) % move.name)
                move._sync_analytic_to_lines()
        return super().action_post()

    # ── Approval Actions ─────────────────────────────────────────────────────

    def action_submit_for_approval(self):
        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund'):
                continue
            if not move.invoice_line_ids:
                raise UserError(_('Tambahkan minimal satu baris COA.'))
            move.x_approval_state = 'waiting'
            move._log_approval('waiting',
                _('Diajukan oleh <b>%s</b>.') % self.env.user.name)
            move._notify_approver()

    def action_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('account_bill_project.group_bill_finance_manager'):
            raise UserError(_('Hanya Finance Manager yang dapat menyetujui.'))
        if self.x_approval_state != 'waiting':
            raise UserError(_('Status tidak sesuai untuk disetujui.'))
        self.write({
            'x_approval_state': 'approved',
            'x_approved_by': self.env.user.id,
            'x_approved_date': fields.Datetime.now(),
            'x_rejected_reason': False,
        })
        self._log_approval('approved',
            _('Disetujui oleh <b>%s</b>.') % self.env.user.name)

    def action_reject(self):
        self.ensure_one()
        if not self.env.user.has_group('account_bill_project.group_bill_finance_manager'):
            raise UserError(_('Hanya Finance Manager yang dapat menolak.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tolak Tagihan'),
            'res_model': 'bill.rejection.wizard',
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

    def _log_approval(self, action, note):
        self.env['account.bill.approval.log'].create({
            'move_id': self.id,
            'user_id': self.env.user.id,
            'action': action,
            'note': note,
        })
        self.message_post(body=note, message_type='notification')

    def _notify_approver(self):
        group = self.env.ref(
            'account_bill_project.group_bill_finance_manager',
            raise_if_not_found=False,
        )
        if not group:
            return
        partner_ids = group.users.mapped('partner_id').ids
        if partner_ids:
            self.message_post(
                body=_('Tagihan <b>%s</b> dari <b>%s</b> total <b>Rp %s</b> menunggu persetujuan.') % (
                    self.name,
                    self.partner_id.name or '-',
                    '{:,.0f}'.format(self.amount_total),
                ),
                partner_ids=partner_ids,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
