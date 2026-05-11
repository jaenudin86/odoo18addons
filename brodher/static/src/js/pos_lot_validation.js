/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EditListPopup } from "@point_of_sale/app/utils/edit_list_popup/edit_list_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(EditListPopup.prototype, {
    async confirm() {
        window.alert("JS OK - Sedang Memvalidasi...");
        // DEBUG: Hapus ini jika sudah muncul
        console.log("[Brodher POS] Tombol OK diklik!");
        
        const title = (this.props.title || "").toLowerCase();
        // Cek apakah ini pop-up Lot atau setidaknya punya input array
        const isLotPopup = title.includes("lot") || title.includes("serial") || this.props.isLot;

        if (isLotPopup || (this.props.array && this.props.array.length > 0)) {
            for (const item of this.state.array) {
                const lotName = (item.text || "").trim();
                if (lotName) {
                    // Cari lot di database lokal POS
                    const lots = this.pos.models['stock.lot'].filter((l) => l.name === lotName);
                    
                    if (lots.length === 0) {
                        this.env.services.popup.add(ErrorPopup, {
                            title: _t("Serial Number Tidak Valid"),
                            body: _t(`Serial Number '${lotName}' tidak ditemukan di sistem!`),
                        });
                        return; 
                    }
                }
            }
        }
        return super.confirm();
    }
});
