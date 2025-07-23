/** @odoo-module **/
import { Component, useRef } from "@odoo/owl";
import { mount } from "@odoo/owl";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { PosMsgView } from "./pos_msg_view";

patch(Navbar.prototype, {
    setup() {
        super.setup();
        this.message = useRef('root');
    },
    onClick(ev) {
        const systrayElements = document.querySelectorAll(".pos_systray_template");
        if (systrayElements.length === 0) {
            this.schedule_dropdown = mount(PosMsgView, document.body);
        } else {
            this.schedule_dropdown?.then((res) => {
                res.__owl__.remove();
            });
        }
    },
});
