/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EditListPopup } from "@point_of_sale/app/utils/edit_list_popup/edit_list_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(EditListPopup.prototype, {
    async confirm() {
        // Deteksi apakah ini pop-up Lot/Serial Number
        const title = (this.props.title || "").toLowerCase();
        const isLotPopup = title.includes("lot") || title.includes("serial") || this.props.isLot;

        if (isLotPopup) {
            console.log("[Brodher POS] Validating Lot Entry...");
            for (const item of this.state.array) {
                const lotName = (item.text || "").trim();
                if (lotName) {
                    // Cari lot di database lokal POS (Odoo 18)
                    const lots = this.pos.models['stock.lot'].filter((l) => l.name === lotName);
                    
                    if (lots.length === 0) {
                        this.env.services.popup.add(ErrorPopup, {
                            title: _t("Serial Number Tidak Valid"),
                            body: _t(`Serial Number '${lotName}' tidak ditemukan di sistem! Anda tidak bisa mengetik sembarangan. Silakan scan QR Code yang valid.`),
                        });
                        return; // Blokir klik OK
                    }
                }
            }
        }
        return super.confirm();
    }
});
