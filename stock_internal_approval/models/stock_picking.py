# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ─── Approval fields ─────────────────────────────────────────────────────
    approval_state = fields.Selection(
        selection=[
            ('not_required', 'Not Required'),
            ('pending',      'Waiting Approval'),
            ('approved',     'Approved'),
            ('refused',      'Refused'),
        ],
        string='Approval Status',
        default='not_required',
        copy=False,
        tracking=True,
        readonly=True,
    )

    approval_required = fields.Boolean(
        string='Approval Required',
        compute='_compute_approval_required',
        store=True,
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True,
    )

    approved_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False,
    )

    refused_by = fields.Many2one(
        'res.users',
        string='Refused By',
        readonly=True,
        copy=False,
        tracking=True,
    )

    refused_reason = fields.Text(
        string='Refusal Reason',
        readonly=True,
        copy=False,
    )

    # ─── Computed ────────────────────────────────────────────────────────────
    @api.depends('picking_type_id', 'picking_type_id.code',
                 'picking_type_id.require_internal_approval')
    def _compute_approval_required(self):
        for picking in self:
            picking.approval_required = (
                picking.picking_type_id.code == 'internal'
                and picking.picking_type_id.require_internal_approval
            )

    # ─── Helpers ─────────────────────────────────────────────────────────────
    def _user_is_creator(self):
        return self.env.user.has_group(
            'stock_internal_approval.group_internal_transfer_creator'
        )

    def _user_is_approver(self):
        return self.env.user.has_group(
            'stock_internal_approval.group_internal_transfer_approver'
        )

    def _user_is_admin(self):
        return (
            self.env.su
            or self.env.user._is_system()
            or self.env.user.has_group('base.group_system')
        )

    # ─── Override create ─────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            picking_type = self.env['stock.picking.type'].browse(
                vals.get('picking_type_id')
            )
            if (
                picking_type.code == 'internal'
                and picking_type.require_internal_approval
                and not self._user_is_creator()
                and not self._user_is_approver()
                and not self._user_is_admin()
            ):
                raise AccessError(_(
                    'You do not have permission to create an internal transfer '
                    'that requires approval.\n\n'
                    'Your administrator must grant you the '
                    '"Internal Transfer Creator" permission.'
                ))

        pickings = super().create(vals_list)

        for picking in pickings:
            if picking.approval_required:
                picking.approval_state = 'pending'

        return pickings

    # ─── Override button_validate ─────────────────────────────────────────────
    def button_validate(self):
        for picking in self:
            if (
                picking.approval_required
                and picking.approval_state != 'approved'
                and not self._user_is_admin()
            ):
                state_label = dict(
                    self._fields['approval_state'].selection
                ).get(picking.approval_state, picking.approval_state)
                raise UserError(_(
                    'Transfer "%s" must be approved before validation.\n'
                    'Current approval status: %s\n\n'
                    'Please contact an approver.'
                ) % (picking.name, state_label))
        return super().button_validate()

    # ─── Approval actions ────────────────────────────────────────────────────
    def action_request_approval(self):
        """Re-submit a refused transfer for approval."""
        for picking in self:
            if not picking.approval_required:
                raise UserError(_('This transfer does not require approval.'))
            if picking.approval_state != 'refused':
                raise UserError(
                    _('Only refused transfers can be re-submitted for approval.')
                )
            picking.write({
                'approval_state': 'pending',
                'refused_by': False,
                'refused_reason': False,
            })
            picking.message_post(
                body=_('Transfer re-submitted for approval by %s.') % self.env.user.name,
                message_type='notification',
            )

    def action_approve_transfer(self):
        """Approve the internal transfer."""
        if not self._user_is_approver() and not self._user_is_admin():
            raise AccessError(_(
                'You do not have the "Internal Transfer Approver" permission.'
            ))
        for picking in self:
            if not picking.approval_required:
                raise UserError(_('This transfer does not require approval.'))
            if picking.approval_state != 'pending':
                raise UserError(_(
                    'Only transfers in "Waiting Approval" status can be approved.'
                ))
            if picking.create_uid == self.env.user and not self._user_is_admin():
                raise UserError(_(
                    'You cannot approve a transfer that you created yourself.\n'
                    'Please ask another approver to review it.'
                ))
            picking.write({
                'approval_state': 'approved',
                'approved_by': self.env.uid,
                'approved_date': fields.Datetime.now(),
                'refused_by': False,
                'refused_reason': False,
            })
            picking.message_post(
                body=_('✅ Transfer approved by %s.') % self.env.user.name,
                message_type='notification',
            )

    def action_refuse_transfer(self):
        """Open the refuse wizard."""
        if not self._user_is_approver() and not self._user_is_admin():
            raise AccessError(_(
                'You do not have the "Internal Transfer Approver" permission.'
            ))
        for picking in self:
            if not picking.approval_required:
                raise UserError(_('This transfer does not require approval.'))
            if picking.approval_state != 'pending':
                raise UserError(_(
                    'Only transfers in "Waiting Approval" status can be refused.'
                ))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Refuse Transfer'),
            'res_model': 'stock.picking.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_ids': self.ids,
            },
        }
