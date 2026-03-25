from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    # === Parent-Child Fields ===
    parent_id = fields.Many2one(
        'account.account',
        string='Parent Account',
        index=True,
        ondelete='restrict',
        domain="[('id', '!=', id)]",
        help='Akun induk untuk membentuk hierarki CoA. '
             'Akun parent berfungsi sebagai penampung/header, '
             'mirip seperti struktur di Accurate.',
    )
    child_ids = fields.One2many(
        'account.account',
        'parent_id',
        string='Child Accounts',
    )
    is_parent = fields.Boolean(
        string='Is Parent Account',
        compute='_compute_is_parent',
        store=True,
        help='Otomatis terceklis jika akun ini memiliki child accounts.',
    )
    hierarchy_level = fields.Integer(
        string='Level',
        compute='_compute_hierarchy_level',
        store=True,
        recursive=True,
        help='Level hierarki akun. Level 0 = akun paling atas (root).',
    )
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True,
        recursive=True,
        help='Nama lengkap termasuk nama parent, misal: Aset / Aset Lancar / Kas',
    )
    child_count = fields.Integer(
        string='Child Count',
        compute='_compute_is_parent',
        store=True,
    )

    # === Compute Methods ===

    @api.depends('child_ids')
    def _compute_is_parent(self):
        for account in self:
            children = account.child_ids
            account.child_count = len(children)
            account.is_parent = bool(children)

    @api.depends('parent_id', 'parent_id.hierarchy_level')
    def _compute_hierarchy_level(self):
        for account in self:
            level = 0
            parent = account.parent_id
            max_depth = 10
            while parent and level < max_depth:
                level += 1
                parent = parent.parent_id
            account.hierarchy_level = level

    @api.depends('name', 'parent_id', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for account in self:
            if account.parent_id:
                account.complete_name = '%s / %s' % (
                    account.parent_id.complete_name or account.parent_id.name,
                    account.name,
                )
            else:
                account.complete_name = account.name

    # === Constraints ===

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """Validasi untuk mencegah circular reference."""
        for account in self:
            if not account.parent_id:
                continue
            if account.parent_id == account:
                raise ValidationError(_(
                    'Error! Akun "%(account)s" tidak bisa menjadi parent dari dirinya sendiri.',
                    account=account.name,
                ))
            parent = account.parent_id
            visited = {account.id}
            max_depth = 10
            depth = 0
            while parent and depth < max_depth:
                if parent.id in visited:
                    raise ValidationError(_(
                        'Error! Circular reference terdeteksi pada akun "%(account)s". '
                        'Pastikan tidak ada akun yang saling merujuk sebagai parent.',
                        account=account.name,
                    ))
                visited.add(parent.id)
                parent = parent.parent_id
                depth += 1

    # === Helper Methods ===

    def get_all_children(self, include_self=False):
        """Mendapatkan semua child accounts secara rekursif."""
        self.ensure_one()
        children = self.env['account.account']
        if include_self:
            children |= self

        def _get_children_recursive(account, depth=0):
            nonlocal children
            if depth > 10:
                return
            for child in account.child_ids:
                children |= child
                _get_children_recursive(child, depth + 1)

        _get_children_recursive(self)
        return children

    def get_all_parents(self, include_self=False):
        """Mendapatkan semua parent accounts sampai root."""
        self.ensure_one()
        parents = self.env['account.account']
        if include_self:
            parents |= self
        parent = self.parent_id
        depth = 0
        while parent and depth < 10:
            parents |= parent
            parent = parent.parent_id
            depth += 1
        return parents

    def get_balance_with_children(self, date_from=None, date_to=None):
        """
        Mendapatkan saldo akun termasuk semua child-nya.
        Berguna untuk report hierarkis.
        """
        self.ensure_one()
        all_accounts = self.get_all_children(include_self=True)

        domain = [('account_id', 'in', all_accounts.ids)]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        move_lines = self.env['account.move.line'].search(domain)
        debit = sum(move_lines.mapped('debit'))
        credit = sum(move_lines.mapped('credit'))
        balance = debit - credit

        return {
            'debit': debit,
            'credit': credit,
            'balance': balance,
        }
