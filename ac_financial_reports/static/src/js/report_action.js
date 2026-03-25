/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function fmt(val) {
    return (val || 0).toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function todayStr() { return new Date().toISOString().slice(0, 10); }
function yearStartStr() { const d = new Date(); return `${d.getFullYear()}-01-01`; }

function collectAccountIds(node) {
    const ids = [node.id];
    if (node.children) {
        for (const child of node.children) {
            ids.push(...collectAccountIds(child));
        }
    }
    return ids;
}

// ================================================================
// HierarchyRow - click on amount triggers drill-down
// ================================================================
class HierarchyRow extends Component {
    static template = "ac_financial_reports.HierarchyRow";
    static props = {
        row: Object, depth: { type: Number, optional: true },
        columns: Array, onDrillDown: { type: Function, optional: true },
    };
    setup() { this.state = useState({ expanded: (this.props.depth || 0) < 1 }); }
    get hasChildren() { return this.props.row.children && this.props.row.children.length > 0; }
    get indent() { return (this.props.depth || 0) * 24; }
    toggleExpand(ev) { ev.stopPropagation(); this.state.expanded = !this.state.expanded; }
    onAmountClick(ev, col) {
        ev.stopPropagation();
        if (this.props.onDrillDown) this.props.onDrillDown(this.props.row, col);
    }
    fmt(val) { return fmt(val); }
}
HierarchyRow.components = { HierarchyRow };

// ================================================================
// TRIAL BALANCE
// ================================================================
class TrialBalanceReport extends Component {
    static template = "ac_financial_reports.TrialBalanceReport";
    static components = { HierarchyRow };
    setup() {
        this.action = useService("action"); this.orm = useService("orm");
        this.state = useState({ data: null, loading: true, dateFrom: yearStartStr(), dateTo: todayStr() });
        onWillStart(() => this.loadData());
    }
    async loadData() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("account.account", "get_trial_balance_data", [], { date_from: this.state.dateFrom, date_to: this.state.dateTo }); }
        catch (e) { console.error(e); }
        this.state.loading = false;
    }
    async onApplyFilter() { await this.loadData(); }
    onDrillDown(row, col) {
        const ids = collectAccountIds(row);
        let domain = [["account_id", "in", ids], ["parent_state", "=", "posted"]];
        if (col.key === "opening_balance") domain.push(["date", "<", this.state.dateFrom]);
        else if (col.key === "ending_balance") domain.push(["date", "<=", this.state.dateTo]);
        else domain.push(["date", ">=", this.state.dateFrom], ["date", "<=", this.state.dateTo]);
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move.line", name: `${row.code} ${row.name} - ${col.label}`, view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain, target: "current" });
    }
    fmt(val) { return fmt(val); }
    get columns() { return [{ key: "opening_balance", label: "Opening" }, { key: "debit", label: "Debit" }, { key: "credit", label: "Credit" }, { key: "ending_balance", label: "Ending" }]; }
}

// ================================================================
// PROFIT & LOSS
// ================================================================
class ProfitLossReport extends Component {
    static template = "ac_financial_reports.ProfitLossReport";
    static components = { HierarchyRow };
    setup() {
        this.action = useService("action"); this.orm = useService("orm");
        this.state = useState({ data: null, loading: true, dateFrom: yearStartStr(), dateTo: todayStr() });
        onWillStart(() => this.loadData());
    }
    async loadData() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("account.account", "get_profit_loss_data", [], { date_from: this.state.dateFrom, date_to: this.state.dateTo }); }
        catch (e) { console.error(e); }
        this.state.loading = false;
    }
    async onApplyFilter() { await this.loadData(); }
    onDrillDown(row, col) {
        const ids = collectAccountIds(row);
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move.line", name: `${row.code} ${row.name}`, view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [["account_id", "in", ids], ["date", ">=", this.state.dateFrom], ["date", "<=", this.state.dateTo], ["parent_state", "=", "posted"]], target: "current" });
    }
    fmt(val) { return fmt(val); }
    get columns() { return [{ key: "balance", label: "Balance" }]; }
}

// ================================================================
// BALANCE SHEET
// ================================================================
class BalanceSheetReport extends Component {
    static template = "ac_financial_reports.BalanceSheetReport";
    static components = { HierarchyRow };
    setup() {
        this.action = useService("action"); this.orm = useService("orm");
        this.state = useState({ data: null, loading: true, dateTo: todayStr() });
        onWillStart(() => this.loadData());
    }
    async loadData() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("account.account", "get_balance_sheet_data", [], { date_to: this.state.dateTo }); }
        catch (e) { console.error(e); }
        this.state.loading = false;
    }
    async onApplyFilter() { await this.loadData(); }
    onDrillDown(row, col) {
        const ids = collectAccountIds(row);
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move.line", name: `${row.code} ${row.name}`, view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [["account_id", "in", ids], ["date", "<=", this.state.dateTo], ["parent_state", "=", "posted"]], target: "current" });
    }
    fmt(val) { return fmt(val); }
    get columns() { return [{ key: "balance", label: "Balance" }]; }
}

// ================================================================
// GENERAL LEDGER (tree list per account, expand to see entries)
// ================================================================
class GeneralLedgerReport extends Component {
    static template = "ac_financial_reports.GeneralLedgerReport";
    setup() {
        this.action = useService("action"); this.orm = useService("orm");
        this.state = useState({ data: null, loading: true, dateFrom: yearStartStr(), dateTo: todayStr(), expandedAccounts: {} });
        onWillStart(() => this.loadData());
    }
    async loadData() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("account.account", "get_general_ledger_data", [], { date_from: this.state.dateFrom, date_to: this.state.dateTo }); this.state.expandedAccounts = {}; }
        catch (e) { console.error(e); }
        this.state.loading = false;
    }
    async onApplyFilter() { await this.loadData(); }
    toggleAccount(accId) { this.state.expandedAccounts[accId] = !this.state.expandedAccounts[accId]; }
    isExpanded(accId) { return !!this.state.expandedAccounts[accId]; }
    onMoveClick(moveId) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move", res_id: moveId, views: [[false, "form"]], target: "current" });
    }
    onOpeningClick(acc) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move.line", name: `${acc.code} - Opening`, view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [["account_id", "=", acc.id], ["date", "<", this.state.dateFrom], ["parent_state", "=", "posted"]], target: "current" });
    }
    onEndingClick(acc) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move.line", name: `${acc.code} - All`, view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [["account_id", "=", acc.id], ["date", "<=", this.state.dateTo], ["parent_state", "=", "posted"]], target: "current" });
    }
    fmt(val) { return fmt(val); }
}

// ================================================================
// CASH FLOW
// ================================================================
class CashFlowReport extends Component {
    static template = "ac_financial_reports.CashFlowReport";
    setup() {
        this.action = useService("action"); this.orm = useService("orm");
        this.state = useState({ data: null, loading: true, dateFrom: yearStartStr(), dateTo: todayStr() });
        onWillStart(() => this.loadData());
    }
    async loadData() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("account.account", "get_cash_flow_data", [], { date_from: this.state.dateFrom, date_to: this.state.dateTo }); }
        catch (e) { console.error(e); }
        this.state.loading = false;
    }
    async onApplyFilter() { await this.loadData(); }
    fmt(val) { return fmt(val); }
}

// ================================================================
// AGING
// ================================================================
class AgingReport extends Component {
    static template = "ac_financial_reports.AgingReport";
    setup() {
        this.action = useService("action"); this.orm = useService("orm");
        this.state = useState({ data: null, loading: true, dateTo: todayStr(), reportType: "receivable", expandedPartners: {} });
        onWillStart(() => this.loadData());
    }
    async loadData() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("account.account", "get_aging_data", [], { date_to: this.state.dateTo, report_type: this.state.reportType }); this.state.expandedPartners = {}; }
        catch (e) { console.error(e); }
        this.state.loading = false;
    }
    async onApplyFilter() { await this.loadData(); }
    setType(type) { this.state.reportType = type; this.loadData(); }
    togglePartner(pid) { this.state.expandedPartners[pid] = !this.state.expandedPartners[pid]; }
    isExpanded(pid) { return !!this.state.expandedPartners[pid]; }
    onPartnerClick(partner) {
        const accType = this.state.reportType === "receivable" ? "asset_receivable" : "liability_payable";
        let domain = [["parent_state", "=", "posted"], ["account_id.account_type", "=", accType], ["reconciled", "=", false]];
        if (partner.partner_id) domain.push(["partner_id", "=", partner.partner_id]);
        else domain.push(["partner_id", "=", false]);
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move.line", name: `${partner.partner_name}`, view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain, target: "current" });
    }
    onMoveClick(moveId) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move", res_id: moveId, views: [[false, "form"]], target: "current" });
    }
    fmt(val) { return fmt(val); }
}

registry.category("actions").add("ac_financial_reports.trial_balance", TrialBalanceReport);
registry.category("actions").add("ac_financial_reports.profit_loss", ProfitLossReport);
registry.category("actions").add("ac_financial_reports.balance_sheet", BalanceSheetReport);
registry.category("actions").add("ac_financial_reports.general_ledger", GeneralLedgerReport);
registry.category("actions").add("ac_financial_reports.cash_flow", CashFlowReport);
registry.category("actions").add("ac_financial_reports.aging_report", AgingReport);
