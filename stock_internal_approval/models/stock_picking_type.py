# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    require_internal_approval = fields.Boolean(
        string='Require Approval for Internal Transfer',
        default=False,
        help=(
            'If checked, internal transfers using this operation type '
            'will require approval from an authorized approver before '
            'they can be validated.'
        ),
    )
