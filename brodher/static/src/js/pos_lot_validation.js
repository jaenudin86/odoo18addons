/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EditListPopup } from "@point_of_sale/app/utils/edit_list_popup/edit_list_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(EditListPopup.prototype, {
    async confirm() {
        // Cek apakah ini pop-up untuk Lot/Serial Number
        const isLotPopup = this.props.title === _t("Lot/Serial Number") || 
                           this.props.title === "Lot/Serial Number" ||
                           (this.props.array && this.props.array.length > 0 && this.props.array[0].text !== undefined);

        if (isLotPopup) {
            for (const item of this.state.array) {
                const lotName = item.text ? item.text.trim() : "";
                if (lotName) {
                    // Cari lot di database lokal POS (Odoo 18)
                    const lots = this.pos.models['stock.lot'].filter((l) => l.name === lotName);
                    
                    if (lots.length === 0) {
                        this.popup.add(ErrorPopup, {
                            title: _t("Serial Number Tidak Valid"),
                            body: _t(`Serial Number '${lotName}' tidak ditemukan di sistem! Anda tidak bisa mengetik sembarangan. Mohon gunakan QR Code yang valid.`),
                        });
                        return; // Berhenti di sini, jangan lanjut confirm
                    }
                }
            }
        }
        return super.confirm();
    }
});
