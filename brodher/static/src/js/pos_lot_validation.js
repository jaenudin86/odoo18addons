/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    async editPackLotLines(line) {
        const result = await super.editPackLotLines(...arguments);
        if (result) {
            const lotLines = line.pack_lot_lines || [];
            for (const lotLine of lotLines) {
                const lotName = (lotLine.lot_name || "").trim();
                if (lotName) {
                    const lots = this.pos.models['stock.lot'].filter((l) => l.name === lotName);
                    if (lots.length === 0) {
                        // Gunakan alert browser saja dulu agar pasti muncul dan tidak butuh import ErrorPopup yang rawan error path
                        window.alert(_t(`Serial Number '${lotName}' tidak ditemukan! Mohon scan QR Code yang valid.`));
                        line.pack_lot_lines = [];
                        return false;
                    }
                }
            }
        }
        return result;
    }
});
