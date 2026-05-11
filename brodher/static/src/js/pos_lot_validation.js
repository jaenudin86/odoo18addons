/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED");

patch(PosStore.prototype, {
    // Kita cegat di level yang lebih tinggi lagi
    async addProductToCurrentOrder(product, options) {
        console.log("[Brodher POS] addProductToCurrentOrder", product.display_name);
        const result = await super.addProductToCurrentOrder(...arguments);
        
        // Cek baris terakhir yang baru masuk
        const order = this.get_order();
        if (order) {
            const lastLine = order.get_last_orderline();
            if (lastLine && lastLine.product_id.tracking === 'serial') {
                this._validateOrderlineLots(lastLine);
            }
        }
        return result;
    },

    // Kita cegat saat user men-scan barcode apa pun
    async _processData(data) {
        const result = await super._processData(...arguments);
        const order = this.get_order();
        if (order) {
            const lastLine = order.get_last_orderline();
            if (lastLine && lastLine.product_id.tracking === 'serial') {
                this._validateOrderlineLots(lastLine);
            }
        }
        return result;
    },

    _validateOrderlineLots(line) {
        const lotLines = line.pack_lot_lines || [];
        const lotNames = lotLines.map(l => l.lot_name);
        
        for (const lotName of lotNames) {
            if (lotName) {
                // Gunakan pencarian yang lebih agresif di database lokal
                const allLots = this.models['stock.lot'] || [];
                const foundLot = allLots.find(l => l.name === lotName.trim());
                
                if (!foundLot) {
                    window.alert(_t(`Serial Number '${lotName}' TIDAK SAH! Sistem akan menghapusnya.`));
                    // Hapus SN yang salah
                    line.pack_lot_lines = [];
                    // Paksa buka kembali pop-up SN agar user mengisi yang benar
                    this.editPackLotLines(line);
                    return false;
                }
            }
        }
        return true;
    }
});
