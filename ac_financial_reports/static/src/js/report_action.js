/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ================================================================
// Shared helper
// ================================================================
function fmt(val) {
    return (val || 0).toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function todayStr() {
    return new Date().toISOString().slice(0, 10);
}

function yearStartStr() {
    const d = new Date();
    return `${d.getFullYear()}-01-01`;
}

// ================================================================
// Reusable HierarchyRow component
// ================================================================
class HierarchyRow extends Component {
    static template = "ac_financial_reports.HierarchyRow";
    static props = {
        row: Object,
        depth: { type: Number, optional: true },
        columns: Array,
        onRowClick: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({ expanded: (this.props.depth || 0) < 1 });
    }

    get hasChildren() {
        return this.props.row.children && this.props.row.children.length > 0;
    }

    get indent() {
        return (this.props.depth || 0) * 24;
    }

    toggleExpand(ev) {
        ev.stopPropagation();
        this.state.expanded = !this.state.expanded;
    }

    onRowClick() {
        if (this.props.onRowClick) {
            this.props.onRowClick(this.props.row.id);
        }
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
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            data: null, loading: true,
            dateFrom: yearStartStr(), dateTo: todayStr(),
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "account.account", "get_trial_balance_data",
                [], { date_from: this.state.dateFrom, date_to: this.state.dateTo }
            );
        } catch (e) { console.error(e); }
        this.state.loading = false;
    }

    async onApplyFilter() { await this.loadData(); }

    onAccountClick(id) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "account.account",
            res_id: id, views: [[false, "form"]], target: "current",
        });
    }

    fmt(val) { return fmt(val); }

    get columns() {
        return [
            { key: "opening_balance", label: "Opening Balance" },
            { key: "debit", label: "Debit" },
            { key: "credit", label: "Credit" },
            { key: "ending_balance", label: "Ending Balance" },
        ];
    }
}

// ================================================================
// PROFIT & LOSS
// ================================================================
class ProfitLossReport extends Component {
    static template = "ac_financial_reports.ProfitLossReport";
    static components = { HierarchyRow };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            data: null, loading: true,
            dateFrom: yearStartStr(), dateTo: todayStr(),
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "account.account", "get_profit_loss_data",
                [], { date_from: this.state.dateFrom, date_to: this.state.dateTo }
            );
        } catch (e) { console.error(e); }
        this.state.loading = false;
    }

    async onApplyFilter() { await this.loadData(); }

    onAccountClick(id) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "account.account",
            res_id: id, views: [[false, "form"]], target: "current",
        });
    }

    fmt(val) { return fmt(val); }

    get columns() {
        return [{ key: "balance", label: "Balance" }];
    }
}

// ================================================================
// BALANCE SHEET
// ================================================================
class BalanceSheetReport extends Component {
    static template = "ac_financial_reports.BalanceSheetReport";
    static components = { HierarchyRow };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            data: null, loading: true, dateTo: todayStr(),
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "account.account", "get_balance_sheet_data",
                [], { date_to: this.state.dateTo }
            );
        } catch (e) { console.error(e); }
        this.state.loading = false;
    }

    async onApplyFilter() { await this.loadData(); }

    onAccountClick(id) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "account.account",
            res_id: id, views: [[false, "form"]], target: "current",
        });
    }

    fmt(val) { return fmt(val); }

    get columns() {
        return [{ key: "balance", label: "Balance" }];
    }
}

// ================================================================
// GENERAL LEDGER
// ================================================================
class GeneralLedgerReport extends Component {
    static template = "ac_financial_reports.GeneralLedgerReport";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            data: null, loading: true,
            dateFrom: yearStartStr(), dateTo: todayStr(),
            expandedAccounts: {},
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "account.account", "get_general_ledger_data",
                [], { date_from: this.state.dateFrom, date_to: this.state.dateTo }
            );
        } catch (e) { console.error(e); }
        this.state.loading = false;
    }

    async onApplyFilter() { await this.loadData(); }

    toggleAccount(accId) {
        this.state.expandedAccounts[accId] = !this.state.expandedAccounts[accId];
    }

    isExpanded(accId) {
        return !!this.state.expandedAccounts[accId];
    }

    onMoveClick(moveId) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "account.move",
            res_id: moveId, views: [[false, "form"]], target: "current",
        });
    }

    fmt(val) { return fmt(val); }
}

// ================================================================
// CASH FLOW
// ================================================================
class CashFlowReport extends Component {
    static template = "ac_financial_reports.CashFlowReport";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            data: null, loading: true,
            dateFrom: yearStartStr(), dateTo: todayStr(),
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "account.account", "get_cash_flow_data",
                [], { date_from: this.state.dateFrom, date_to: this.state.dateTo }
            );
        } catch (e) { console.error(e); }
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
        this.orm = useService("orm");
        this.state = useState({
            data: null, loading: true,
            dateTo: todayStr(), reportType: "receivable",
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "account.account", "get_aging_data",
                [], { date_to: this.state.dateTo, report_type: this.state.reportType }
            );
        } catch (e) { console.error(e); }
        this.state.loading = false;
    }

    async onApplyFilter() { await this.loadData(); }

    setType(type) {
        this.state.reportType = type;
        this.loadData();
    }

    fmt(val) { return fmt(val); }
}

// ================================================================
// Register all actions
// ================================================================
registry.category("actions").add("ac_financial_reports.trial_balance", TrialBalanceReport);
registry.category("actions").add("ac_financial_reports.profit_loss", ProfitLossReport);
registry.category("actions").add("ac_financial_reports.balance_sheet", BalanceSheetReport);
registry.category("actions").add("ac_financial_reports.general_ledger", GeneralLedgerReport);
registry.category("actions").add("ac_financial_reports.cash_flow", CashFlowReport);
registry.category("actions").add("ac_financial_reports.aging_report", AgingReport);
