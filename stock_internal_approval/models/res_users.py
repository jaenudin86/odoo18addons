# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    # ─── Internal Transfer Creator ───────────────────────────────────────────
    # Odoo's standard pattern: boolean field linked to a group.
    # When the checkbox is ticked the user is added to the group;
    # when unticked they are removed.

    is_internal_transfer_creator = fields.Boolean(
        string='Internal Transfer Creator',
        compute='_compute_internal_transfer_groups',
        inverse='_inverse_internal_transfer_creator',
        store=False,
        help=(
            'If checked, this user can create internal transfers '
            'that require approval.'
        ),
    )

    is_internal_transfer_approver = fields.Boolean(
        string='Internal Transfer Approver',
        compute='_compute_internal_transfer_groups',
        inverse='_inverse_internal_transfer_approver',
        store=False,
        help=(
            'If checked, this user can approve or refuse internal transfers '
            'created by other users.'
        ),
    )

    @api.depends('groups_id')
    def _compute_internal_transfer_groups(self):
        creator_group = self.env.ref(
            'stock_internal_approval.group_internal_transfer_creator',
            raise_if_not_found=False,
        )
        approver_group = self.env.ref(
            'stock_internal_approval.group_internal_transfer_approver',
            raise_if_not_found=False,
        )
        for user in self:
            user.is_internal_transfer_creator = (
                creator_group in user.groups_id if creator_group else False
            )
            user.is_internal_transfer_approver = (
                approver_group in user.groups_id if approver_group else False
            )

    def _inverse_internal_transfer_creator(self):
        creator_group = self.env.ref(
            'stock_internal_approval.group_internal_transfer_creator'
        )
        for user in self:
            if user.is_internal_transfer_creator:
                user.sudo().groups_id = [(4, creator_group.id)]
            else:
                user.sudo().groups_id = [(3, creator_group.id)]

    def _inverse_internal_transfer_approver(self):
        approver_group = self.env.ref(
            'stock_internal_approval.group_internal_transfer_approver'
        )
        for user in self:
            if user.is_internal_transfer_approver:
                user.sudo().groups_id = [(4, approver_group.id)]
            else:
                user.sudo().groups_id = [(3, approver_group.id)]

    def _is_admin(self):
        """Check if user is Odoo administrator."""
        return self.env.su or self._is_system()
