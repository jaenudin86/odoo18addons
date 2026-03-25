/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class CoAHierarchyRow extends Component {
    static template = "ac_coa_hierarchy.CoAHierarchyRow";
    static props = {
        account: Object,
        depth: { type: Number, optional: true },
        onAccountClick: Function,
    };

    setup() {
        this.state = useState({ expanded: this.props.depth < 1 });
    }

    get hasChildren() {
        return this.props.account.children && this.props.account.children.length > 0;
    }

    get indent() {
        return (this.props.depth || 0) * 24;
    }

    toggleExpand(ev) {
        ev.stopPropagation();
        this.state.expanded = !this.state.expanded;
    }

    onRowClick() {
        this.props.onAccountClick(this.props.account.id);
    }
}
CoAHierarchyRow.components = { CoAHierarchyRow };

class CoAHierarchyView extends Component {
    static template = "ac_coa_hierarchy.CoAHierarchyView";
    static components = { CoAHierarchyRow };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rpc = useService("rpc");

        this.state = useState({
            accounts: [],
            total: 0,
            loading: true,
            searchQuery: "",
            expandAll: false,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await this.rpc("/ac_coa_hierarchy/get_hierarchy", {});
            this.state.accounts = result.accounts || [];
            this.state.total = result.total || 0;
        } catch (e) {
            console.error("Error loading CoA hierarchy:", e);
            this.state.accounts = [];
        }
        this.state.loading = false;
    }

    get filteredAccounts() {
        const query = this.state.searchQuery.toLowerCase().trim();
        if (!query) {
            return this.state.accounts;
        }
        return this._filterTree(this.state.accounts, query);
    }

    _filterTree(accounts, query) {
        const result = [];
        for (const acc of accounts) {
            const nameMatch = (acc.name || "").toLowerCase().includes(query);
            const codeMatch = (acc.code || "").toLowerCase().includes(query);
            const filteredChildren = this._filterTree(acc.children || [], query);

            if (nameMatch || codeMatch || filteredChildren.length > 0) {
                result.push({
                    ...acc,
                    children: filteredChildren.length > 0 ? filteredChildren : acc.children,
                });
            }
        }
        return result;
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onAccountClick(accountId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.account",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onRefresh() {
        await this.loadData();
    }

    formatBalance(balance) {
        return (balance || 0).toLocaleString("id-ID", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}

registry.category("actions").add("ac_coa_hierarchy.hierarchy_view", CoAHierarchyView);
