/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

// ALERT TEST: Jika ini tidak muncul saat POS dibuka, berarti file JS tidak ter-load
console.log("POS LOT VALIDATION LOADED");
window.alert("VALIDASI AKTIF"); 

// JARING 1: Di PosStore (Pusat Data)
patch(PosStore.prototype, {
    async editPackLotLines(line) {
        console.log("[Brodher POS] editPackLotLines PosStore triggered");
        const result = await super.editPackLotLines(...arguments);
        if (result) {
            this._validateLineLots(line);
        }
        return result;
    },

    _validateLineLots(line) {
        const lotLines = line.pack_lot_lines || [];
        for (const lotLine of lotLines) {
            const lotName = (lotLine.lot_name || "").trim();
            if (lotName) {
                const foundLot = this.models['stock.lot'].find(l => l.name === lotName);
                if (!foundLot) {
                    window.alert(_t(`Serial Number '${lotName}' TIDAK SAH! Mohon gunakan QR Code.`));
                    line.pack_lot_lines = [];
                    return false;
                }
            }
        }
        return true;
    }
});

// JARING 2: Di ProductScreen (Layar Utama)
patch(ProductScreen.prototype, {
    async editPackLotLines(line) {
        console.log("[Brodher POS] editPackLotLines ProductScreen triggered");
        const result = await super.editPackLotLines(...arguments);
        if (result) {
            const lotNames = line.pack_lot_lines.map(l => l.lot_name);
            const foundInvalid = lotNames.some(name => {
                const found = this.pos.models['stock.lot'].find(l => l.name === name.trim());
                return !found;
            });

            if (foundInvalid) {
                window.alert(_t("Ada Serial Number yang tidak valid! Pesanan dibatalkan."));
                line.pack_lot_lines = [];
                return false;
            }
        }
        return result;
    }
});
