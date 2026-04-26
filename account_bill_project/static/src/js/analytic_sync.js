/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useEffect } from "@odoo/owl";

/**
 * Sync analytic dari header ke semua invoice_line_ids.
 * invoice_line_ids di Odoo 18 adalah StaticList, bukan Array biasa.
 * Gunakan model.root.data untuk akses data, dan
 * model.root.updateRecord untuk update per record.
 */
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        useEffect(
            () => {
                this._syncAnalyticToLines();
            },
            () => [
                this.model?.root?.data?.x_analytic_account_id?.[0],
                this.model?.root?.data?.x_analytic_distribution_pct,
            ]
        );
    },

    _syncAnalyticToLines() {
        const root = this.model?.root;
        if (!root) return;
        if (root.resModel !== "account.move") return;

        const moveType = root.data?.move_type;
        if (!["in_invoice", "in_refund"].includes(moveType)) return;

        const analyticRaw = root.data?.x_analytic_account_id;
        // Many2one value bisa [id, name] atau false
        const analyticId = Array.isArray(analyticRaw) ? analyticRaw[0] : analyticRaw;
        if (!analyticId) return;

        const pct = root.data?.x_analytic_distribution_pct ?? 100.0;
        const distribution = { [String(analyticId)]: pct };

        // invoice_line_ids adalah StaticList — ambil via root.data
        const lineList = root.data?.invoice_line_ids;
        if (!lineList) return;

        // StaticList punya property 'records' (array of Record)
        const records = lineList.records ?? lineList;
        if (!records || typeof records[Symbol.iterator] !== "function") return;

        for (const line of records) {
            if (line.data?.display_type === "product") {
                // update() hanya untuk field yang bisa diedit
                line.update({ analytic_distribution: distribution }).catch(() => {});
            }
        }
    },
});
