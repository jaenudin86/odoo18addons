/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AbstractAwaitablePopup } from "@point_of_sale/app/utils/abstract_awaitable_popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED");

patch(AbstractAwaitablePopup.prototype, {
    async confirm() {
        const title = (this.props.title || "").toLowerCase();
        // Cek apakah ini pop-up Lot/Serial
        const isLotPopup = title.includes("lot") || title.includes("serial") || this.props.isLot;

        if (isLotPopup) {
            // Kita ambil data dari state pop-up (biasanya array untuk EditListPopup)
            const items = this.state.array || [];
            console.log("[Brodher POS] Validating Popup Items:", items);
            
            for (const item of items) {
                const lotName = (item.text || "").trim();
                if (lotName) {
                    // Cari di database lokal
                    const pos = this.env.services.pos;
                    const allLots = pos.models['stock.lot'] || [];
                    const foundLot = allLots.find(l => l.name === lotName);
                    
                    if (!foundLot) {
                        window.alert(_t(`Serial Number '${lotName}' TIDAK DITEMUKAN di sistem! Mohon gunakan QR Code yang valid.`));
                        // Jangan lanjut confirm, biarkan user memperbaiki inputnya
                        return; 
                    }
                }
            }
        }
        return super.confirm();
    }
});

import { PosStore } from "@point_of_sale/app/store/pos_store";
patch(PosStore.prototype, {
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }
        if (code && code.length > 5) {
            const allLots = this.models['stock.lot'] || [];
            const foundLot = allLots.find(l => l.name === code);
            const foundProduct = this.models['product.product'].find(p => p.barcode === code);
            
            if (!foundLot && !foundProduct) {
                window.alert(_t(`Kode '${code}' tidak dikenal sebagai Produk atau Serial Number yang sah!`));
                return false;
            }
        }
        return super.scan_barcode(code);
    }
});
