/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class SNPrintProgressBar extends Component {
    static template = "brodher_product_serial.SNPrintProgressBar";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            progress: 0,
            statusText: "Initializing...",
            isFinished: false,
        });

        onWillStart(async () => {
            await this._processNextBatch();
        });
    }

    async _processNextBatch() {
        const res = await this.orm.call(
            "brodher.sn.print.wizard",
            "action_process_next_batch",
            [this.props.action.params.wizard_id]
        );

        if (res === true) {
            // Get updated progress
            const wizard = await this.orm.read("brodher.sn.print.wizard", [this.props.action.params.wizard_id], ["progress", "current_batch", "total_batches"]);
            this.state.progress = wizard[0].progress;
            this.state.statusText = `Memproses Batch ${wizard[0].current_batch} dari ${wizard[0].total_batches}...`;
            
            // Short delay to show progress movement
            setTimeout(() => {
                this._processNextBatch();
            }, 300);
        } else if (res && typeof res === 'object' && res.type === 'ir.actions.act_url') {
            // Finished! Download file
            this.state.progress = 100;
            this.state.statusText = "Selesai! Memulai download...";
            this.state.isFinished = true;
            this.action.doAction(res);
            
            // Close wizard after a delay
            setTimeout(() => {
                this.action.doAction({ type: 'ir.actions.act_window_close' });
            }, 2000);
        }
    }
}

registry.category("actions").add("sn_print_progress_action", SNPrintProgressBar);
