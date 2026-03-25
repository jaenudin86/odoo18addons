/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useEffect } from "@odoo/owl";

/**
 * Patch FormController untuk account.move:
 * Setiap kali x_analytic_account_id atau x_analytic_percentage berubah,
 * semua baris invoice_line_ids ikut ter-update otomatis (analytic_distribution).
 */
patch(FormController.prototype, {

    setup() {
        super.setup(...arguments);

        useEffect(
            () => {
                const model = this.model?.root;
                if (!model) return;

                // Hanya untuk account.move
                if (model.resModel !== "account.move") return;

                const moveType = model.data?.move_type;
                if (!["in_invoice", "in_refund"].includes(moveType)) return;

                const analyticId  = model.data?.x_analytic_account_id?.[0];
                const analyticPct = model.data?.x_analytic_percentage ?? 100.0;

                if (!analyticId) return;

                // Build distribution JSON: { "analytic_account_id": percentage }
                const distribution = { [String(analyticId)]: analyticPct };

                // Sync ke setiap invoice line
                const lines = model.data?.invoice_line_ids ?? [];
                lines.forEach((line) => {
                    if (line.data?.display_type === "product") {
                        line.update({ analytic_distribution: distribution });
                    }
                });
            },
            // Re-run setiap kali analytic account atau persentase berubah
            () => [
                this.model?.root?.data?.x_analytic_account_id,
                this.model?.root?.data?.x_analytic_percentage,
            ]
        );
    },
});
