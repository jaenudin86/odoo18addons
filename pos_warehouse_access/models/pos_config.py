# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    user_access_ids = fields.Many2many(
        'res.users',
        'pos_user_access_rel',
        'pos_id',
        'user_id',
        string='User Access',
        help='User yang bisa mengakses POS ini'
    )
    
    user_access_count = fields.Integer(
        string='User Access Count',
        compute='_compute_user_access_count'
    )
    
    @api.depends('user_access_ids')
    def _compute_user_access_count(self):
        for pos in self:
            pos.user_access_count = len(pos.user_access_ids)
    
    def action_view_user_access(self):
        """Open list view of users that can access this POS"""
        self.ensure_one()
        return {
            'name': 'User Access',
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.user_access_ids.ids)],
            'context': {'default_pos_access_ids': [(4, self.id)]},
        }
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to filter POS based on user access"""
        if domain is None:
            domain = []
        
        # Check if user is POS Manager or Admin
        if not self.env.user.has_group('point_of_sale.group_pos_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by access
            allowed_pos_ids = self.env.user.pos_access_ids.ids
            if allowed_pos_ids:
                domain = ['&', ('id', 'in', allowed_pos_ids)] + domain
            else:
                # No access to any POS
                domain = [('id', '=', False)] + domain
        
        return super(PosConfig, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )
