from odoo import api, fields, models, _
from datetime import date
from collections import defaultdict


class AccountAccountReports(models.Model):
    _inherit = 'account.account'

    # ================================================================
    # TRIAL BALANCE
    # ================================================================
    @api.model
    def get_trial_balance_data(self, date_from=None, date_to=None):
        if not date_to:
            date_to = fields.Date.today().strftime('%Y-%m-%d')
        if not date_from:
            today = fields.Date.today()
            date_from = date(today.year, 1, 1).strftime('%Y-%m-%d')

        Account = self.env['account.account']
        MoveLine = self.env['account.move.line']
        accounts = Account.search([], order='code')

        opening_data = {}
        opening_lines = MoveLine.read_group(
            [('date', '<', date_from), ('parent_state', '=', 'posted')],
            ['account_id', 'debit', 'credit'],
            ['account_id'],
        )
        for line in opening_lines:
            acc_id = line['account_id'][0]
            opening_data[acc_id] = {
                'debit': line['debit'] or 0.0,
                'credit': line['credit'] or 0.0,
            }

        period_data = {}
        period_lines = MoveLine.read_group(
            [('date', '>=', date_from), ('date', '<=', date_to), ('parent_state', '=', 'posted')],
            ['account_id', 'debit', 'credit'],
            ['account_id'],
        )
        for line in period_lines:
            acc_id = line['account_id'][0]
            period_data[acc_id] = {
                'debit': line['debit'] or 0.0,
                'credit': line['credit'] or 0.0,
            }

        account_map = {}
        children_map = defaultdict(list)

        for acc in accounts:
            o = opening_data.get(acc.id, {'debit': 0, 'credit': 0})
            p = period_data.get(acc.id, {'debit': 0, 'credit': 0})
            opening_balance = o['debit'] - o['credit']

            account_map[acc.id] = {
                'id': acc.id,
                'code': acc.code or '',
                'name': acc.name or '',
                'account_type': acc.account_type or '',
                'parent_id': acc.parent_id.id if acc.parent_id else False,
                'is_parent': acc.is_parent,
                'hierarchy_level': acc.hierarchy_level,
                'opening_balance': opening_balance,
                'debit': p['debit'],
                'credit': p['credit'],
                'ending_balance': opening_balance + p['debit'] - p['credit'],
                'children': [],
            }
            parent_key = acc.parent_id.id if acc.parent_id else 0
            children_map[parent_key].append(acc.id)

        def build_tree(parent_key):
            result = []
            for acc_id in children_map.get(parent_key, []):
                node = dict(account_map[acc_id])
                node['children'] = build_tree(acc_id)
                for child in node['children']:
                    node['opening_balance'] += child['opening_balance']
                    node['debit'] += child['debit']
                    node['credit'] += child['credit']
                    node['ending_balance'] += child['ending_balance']
                result.append(node)
            return result

        tree = build_tree(0)
        totals = {'opening_balance': 0, 'debit': 0, 'credit': 0, 'ending_balance': 0}
        for node in tree:
            totals['opening_balance'] += node['opening_balance']
            totals['debit'] += node['debit']
            totals['credit'] += node['credit']
            totals['ending_balance'] += node['ending_balance']

        return {
            'report_name': 'Trial Balance',
            'date_from': date_from,
            'date_to': date_to,
            'accounts': tree,
            'totals': totals,
        }

    # ================================================================
    # PROFIT & LOSS
    # ================================================================
    @api.model
    def get_profit_loss_data(self, date_from=None, date_to=None):
        if not date_to:
            date_to = fields.Date.today().strftime('%Y-%m-%d')
        if not date_from:
            today = fields.Date.today()
            date_from = date(today.year, 1, 1).strftime('%Y-%m-%d')

        Account = self.env['account.account']
        MoveLine = self.env['account.move.line']

        income_types = ['income', 'income_other']
        expense_types = ['expense', 'expense_depreciation', 'expense_direct_cost']

        pl_accounts = Account.search([
            ('account_type', 'in', income_types + expense_types),
        ], order='code')

        move_data = {}
        lines = MoveLine.read_group(
            [('date', '>=', date_from), ('date', '<=', date_to),
             ('parent_state', '=', 'posted'),
             ('account_id.account_type', 'in', income_types + expense_types)],
            ['account_id', 'debit', 'credit'],
            ['account_id'],
        )
        for line in lines:
            acc_id = line['account_id'][0]
            move_data[acc_id] = {'debit': line['debit'] or 0.0, 'credit': line['credit'] or 0.0}

        def build_section(acc_types, sign=1):
            accs = pl_accounts.filtered(lambda a: a.account_type in acc_types)
            account_map = {}
            children_map = defaultdict(list)
            for acc in accs:
                d = move_data.get(acc.id, {'debit': 0, 'credit': 0})
                balance = (d['credit'] - d['debit']) * sign
                account_map[acc.id] = {
                    'id': acc.id, 'code': acc.code or '', 'name': acc.name or '',
                    'account_type': acc.account_type or '',
                    'parent_id': acc.parent_id.id if acc.parent_id else False,
                    'is_parent': acc.is_parent, 'hierarchy_level': acc.hierarchy_level,
                    'balance': balance, 'debit': d['debit'], 'credit': d['credit'],
                    'children': [],
                }
                parent_key = acc.parent_id.id if acc.parent_id else 0
                children_map[parent_key].append(acc.id)

            def build_tree(pk):
                res = []
                for aid in children_map.get(pk, []):
                    node = dict(account_map[aid])
                    node['children'] = build_tree(aid)
                    for child in node['children']:
                        node['balance'] += child['balance']
                    res.append(node)
                return res

            items = build_tree(0)
            total = sum(n['balance'] for n in items)
            return items, total

        income_items, total_income = build_section(income_types, sign=1)
        expense_items, total_expense = build_section(expense_types, sign=-1)

        return {
            'report_name': 'Profit & Loss',
            'date_from': date_from, 'date_to': date_to,
            'income': {'items': income_items, 'total': total_income},
            'expense': {'items': expense_items, 'total': total_expense},
            'net_profit': total_income - total_expense,
        }

    # ================================================================
    # BALANCE SHEET
    # ================================================================
    @api.model
    def get_balance_sheet_data(self, date_to=None):
        if not date_to:
            date_to = fields.Date.today().strftime('%Y-%m-%d')

        Account = self.env['account.account']
        MoveLine = self.env['account.move.line']

        asset_types = ['asset_receivable', 'asset_cash', 'asset_current',
                       'asset_non_current', 'asset_prepayments', 'asset_fixed']
        liability_types = ['liability_payable', 'liability_current', 'liability_non_current']
        equity_types = ['equity', 'equity_unaffected']
        all_types = asset_types + liability_types + equity_types

        bs_accounts = Account.search([('account_type', 'in', all_types)], order='code')

        move_data = {}
        lines = MoveLine.read_group(
            [('date', '<=', date_to), ('parent_state', '=', 'posted'),
             ('account_id.account_type', 'in', all_types)],
            ['account_id', 'debit', 'credit'], ['account_id'],
        )
        for line in lines:
            acc_id = line['account_id'][0]
            move_data[acc_id] = {'debit': line['debit'] or 0.0, 'credit': line['credit'] or 0.0}

        # Unallocated earnings
        income_types = ['income', 'income_other']
        expense_types = ['expense', 'expense_depreciation', 'expense_direct_cost']
        pl_lines = MoveLine.read_group(
            [('date', '<=', date_to), ('parent_state', '=', 'posted'),
             ('account_id.account_type', 'in', income_types + expense_types)],
            ['debit', 'credit'], [],
        )
        unallocated = 0
        if pl_lines:
            unallocated = (pl_lines[0].get('credit', 0) or 0) - (pl_lines[0].get('debit', 0) or 0)

        def build_section(acc_types, sign=1):
            accs = bs_accounts.filtered(lambda a: a.account_type in acc_types)
            account_map = {}
            children_map = defaultdict(list)
            for acc in accs:
                d = move_data.get(acc.id, {'debit': 0, 'credit': 0})
                balance = (d['debit'] - d['credit']) * sign
                account_map[acc.id] = {
                    'id': acc.id, 'code': acc.code or '', 'name': acc.name or '',
                    'account_type': acc.account_type or '',
                    'parent_id': acc.parent_id.id if acc.parent_id else False,
                    'is_parent': acc.is_parent, 'hierarchy_level': acc.hierarchy_level,
                    'balance': balance, 'children': [],
                }
                pk = acc.parent_id.id if acc.parent_id else 0
                children_map[pk].append(acc.id)

            def build_tree(pk):
                res = []
                for aid in children_map.get(pk, []):
                    node = dict(account_map[aid])
                    node['children'] = build_tree(aid)
                    for c in node['children']:
                        node['balance'] += c['balance']
                    res.append(node)
                return res

            items = build_tree(0)
            total = sum(n['balance'] for n in items)
            return items, total

        asset_items, total_assets = build_section(asset_types, sign=1)
        liability_items, total_liabilities = build_section(liability_types, sign=-1)
        equity_items, total_equity = build_section(equity_types, sign=-1)

        return {
            'report_name': 'Balance Sheet', 'date_to': date_to,
            'assets': {'items': asset_items, 'total': total_assets},
            'liabilities': {'items': liability_items, 'total': total_liabilities},
            'equity': {'items': equity_items, 'total': total_equity},
            'unallocated_earnings': unallocated,
            'total_equity_with_earnings': total_equity + unallocated,
            'total_liabilities_equity': total_liabilities + total_equity + unallocated,
        }

    # ================================================================
    # GENERAL LEDGER
    # ================================================================
    @api.model
    def get_general_ledger_data(self, date_from=None, date_to=None, account_ids=None):
        if not date_to:
            date_to = fields.Date.today().strftime('%Y-%m-%d')
        if not date_from:
            today = fields.Date.today()
            date_from = date(today.year, 1, 1).strftime('%Y-%m-%d')

        Account = self.env['account.account']
        MoveLine = self.env['account.move.line']

        acc_domain = [('id', 'in', account_ids)] if account_ids else []
        accounts = Account.search(acc_domain, order='code')

        result = []
        for acc in accounts:
            opening_lines = MoveLine.search([
                ('account_id', '=', acc.id), ('date', '<', date_from),
                ('parent_state', '=', 'posted'),
            ])
            opening_balance = sum(opening_lines.mapped('debit')) - sum(opening_lines.mapped('credit'))

            period_lines = MoveLine.search([
                ('account_id', '=', acc.id), ('date', '>=', date_from),
                ('date', '<=', date_to), ('parent_state', '=', 'posted'),
            ], order='date, id')

            entries = []
            running = opening_balance
            for ml in period_lines:
                running += ml.debit - ml.credit
                entries.append({
                    'id': ml.id, 'date': ml.date.strftime('%Y-%m-%d') if ml.date else '',
                    'move_name': ml.move_id.name or '', 'move_id': ml.move_id.id,
                    'partner': ml.partner_id.name if ml.partner_id else '',
                    'label': ml.name or '',
                    'debit': ml.debit, 'credit': ml.credit, 'balance': running,
                })

            if entries or opening_balance != 0:
                result.append({
                    'id': acc.id, 'code': acc.code or '', 'name': acc.name or '',
                    'opening_balance': opening_balance, 'entries': entries,
                    'total_debit': sum(e['debit'] for e in entries),
                    'total_credit': sum(e['credit'] for e in entries),
                    'ending_balance': running if entries else opening_balance,
                })

        return {
            'report_name': 'General Ledger',
            'date_from': date_from, 'date_to': date_to,
            'accounts': result,
        }

    # ================================================================
    # CASH FLOW (INDIRECT)
    # ================================================================
    @api.model
    def get_cash_flow_data(self, date_from=None, date_to=None):
        if not date_to:
            date_to = fields.Date.today().strftime('%Y-%m-%d')
        if not date_from:
            today = fields.Date.today()
            date_from = date(today.year, 1, 1).strftime('%Y-%m-%d')

        MoveLine = self.env['account.move.line']
        base_domain = [('date', '>=', date_from), ('date', '<=', date_to), ('parent_state', '=', 'posted')]

        income_types = ['income', 'income_other']
        expense_types = ['expense', 'expense_depreciation', 'expense_direct_cost']
        pl_lines = MoveLine.search(base_domain + [
            ('account_id.account_type', 'in', income_types + expense_types)])
        net_income = sum(pl_lines.mapped('credit')) - sum(pl_lines.mapped('debit'))

        dep_lines = MoveLine.search(base_domain + [('account_id.account_type', '=', 'expense_depreciation')])
        depreciation = sum(dep_lines.mapped('debit')) - sum(dep_lines.mapped('credit'))

        def get_change(acc_type):
            ls = MoveLine.search(base_domain + [('account_id.account_type', '=', acc_type)])
            return sum(ls.mapped('debit')) - sum(ls.mapped('credit'))

        rc = -get_change('asset_receivable')
        pc = -get_change('liability_payable')
        ppc = -get_change('asset_prepayments')
        cac = -get_change('asset_current')
        clc = -get_change('liability_current')
        operating_total = net_income + depreciation + rc + pc + ppc + cac + clc

        fac = -get_change('asset_fixed')
        ncac = -get_change('asset_non_current')
        investing_total = fac + ncac

        ec = -get_change('equity')
        nclc = -get_change('liability_non_current')
        financing_total = ec + nclc

        net_cash = operating_total + investing_total + financing_total

        opening_cash_lines = MoveLine.search([
            ('date', '<', date_from), ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_cash')])
        opening_cash = sum(opening_cash_lines.mapped('debit')) - sum(opening_cash_lines.mapped('credit'))

        return {
            'report_name': 'Cash Flow Statement',
            'date_from': date_from, 'date_to': date_to,
            'operating': {
                'net_income': net_income,
                'adjustments': [{'name': 'Depreciation & Amortization', 'amount': depreciation}],
                'working_capital': [
                    {'name': 'Change in Receivables', 'amount': rc},
                    {'name': 'Change in Payables', 'amount': pc},
                    {'name': 'Change in Prepayments', 'amount': ppc},
                    {'name': 'Change in Other Current Assets', 'amount': cac},
                    {'name': 'Change in Other Current Liabilities', 'amount': clc},
                ],
                'total': operating_total,
            },
            'investing': {
                'items': [
                    {'name': 'Change in Fixed Assets', 'amount': fac},
                    {'name': 'Change in Non-Current Assets', 'amount': ncac},
                ],
                'total': investing_total,
            },
            'financing': {
                'items': [
                    {'name': 'Change in Equity', 'amount': ec},
                    {'name': 'Change in Non-Current Liabilities', 'amount': nclc},
                ],
                'total': financing_total,
            },
            'net_cash_change': net_cash,
            'opening_cash': opening_cash,
            'closing_cash': opening_cash + net_cash,
        }

    # ================================================================
    # AGING REPORT
    # ================================================================
    @api.model
    def get_aging_data(self, date_to=None, report_type='receivable'):
        if not date_to:
            date_to = fields.Date.today().strftime('%Y-%m-%d')

        date_to_obj = fields.Date.from_string(date_to)
        MoveLine = self.env['account.move.line']
        acc_type = 'asset_receivable' if report_type == 'receivable' else 'liability_payable'

        lines = MoveLine.search([
            ('account_id.account_type', '=', acc_type),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('date', '<=', date_to),
        ], order='partner_id, date')

        partner_data = defaultdict(lambda: {
            'current': 0, 'b1_30': 0, 'b31_60': 0, 'b61_90': 0, 'b90_plus': 0, 'total': 0,
        })

        for ml in lines:
            pname = ml.partner_id.name if ml.partner_id else 'No Partner'
            pid = ml.partner_id.id if ml.partner_id else 0
            amount = ml.amount_residual or (ml.debit - ml.credit)
            age = (date_to_obj - ml.date).days if ml.date else 0
            key = (pid, pname)

            if age <= 0:
                partner_data[key]['current'] += amount
            elif age <= 30:
                partner_data[key]['b1_30'] += amount
            elif age <= 60:
                partner_data[key]['b31_60'] += amount
            elif age <= 90:
                partner_data[key]['b61_90'] += amount
            else:
                partner_data[key]['b90_plus'] += amount
            partner_data[key]['total'] += amount

        result = []
        for (pid, pname), data in sorted(partner_data.items(), key=lambda x: x[0][1]):
            result.append({'partner_id': pid, 'partner_name': pname, **data})

        totals = {k: sum(r[k] for r in result) for k in ['current', 'b1_30', 'b31_60', 'b61_90', 'b90_plus', 'total']}

        return {
            'report_name': 'Aging %s' % ('Receivable' if report_type == 'receivable' else 'Payable'),
            'report_type': report_type, 'date_to': date_to,
            'partners': result, 'totals': totals,
        }
