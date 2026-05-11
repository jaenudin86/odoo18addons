/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    async editPackLotLines(line) {
        const result = await super.editPackLotLines(...arguments);
        
        if (result) {
            // Ambil daftar SN yang diinput user
            const lotLines = line.pack_lot_lines || [];
            
            for (const lotLine of lotLines) {
                const lotName = (lotLine.lot_name || "").trim();
                if (lotName) {
                    // Cari lot di database lokal POS (Odoo 18)
                    const lots = this.pos.models['stock.lot'].filter((l) => l.name === lotName);
                    
                    if (lots.length === 0) {
                        this.popup.add(ErrorPopup, {
                            title: _t("Serial Number Tidak Valid"),
                            body: _t(`Nomor seri '${lotName}' tidak ditemukan! Anda tidak bisa memasukkan nomor asal.`),
                        });
                        
                        // Kosongkan SN yang salah agar tidak bisa lanjut bayar
                        line.pack_lot_lines = [];
                        return false;
                    }
                }
            }
        }
        return result;
    }
});
