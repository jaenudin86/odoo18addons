from odoo import http
from odoo.http import request
import json


class CoAHierarchyController(http.Controller):

    @http.route('/ac_coa_hierarchy/get_hierarchy', type='json', auth='user')
    def get_hierarchy(self, **kwargs):
        """Return CoA hierarchy data as nested tree structure."""
        accounts = request.env['account.account'].search([], order='code')

        # Build lookup maps
        account_map = {}
        children_map = {}

        for acc in accounts:
            account_map[acc.id] = {
                'id': acc.id,
                'code': acc.code or '',
                'name': acc.name or '',
                'complete_name': acc.complete_name or acc.name or '',
                'account_type': acc.account_type or '',
                'account_type_label': dict(
                    acc._fields['account_type'].selection
                ).get(acc.account_type, acc.account_type or ''),
                'parent_id': acc.parent_id.id if acc.parent_id else False,
                'is_parent': acc.is_parent,
                'hierarchy_level': acc.hierarchy_level,
                'child_count': acc.child_count,
                'current_balance': acc.current_balance,
                'reconcile': acc.reconcile,
                'deprecated': acc.deprecated,
            }
            parent_key = acc.parent_id.id if acc.parent_id else 0
            if parent_key not in children_map:
                children_map[parent_key] = []
            children_map[parent_key].append(acc.id)

        def build_tree(parent_key):
            result = []
            for acc_id in children_map.get(parent_key, []):
                node = dict(account_map[acc_id])
                node['children'] = build_tree(acc_id)
                result.append(node)
            return result

        tree = build_tree(0)
        return {'accounts': tree, 'total': len(accounts)}
