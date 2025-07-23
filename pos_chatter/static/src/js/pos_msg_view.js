/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";
const { mount, xml, onMounted, useState, useRef } = owl;
import { ChatMsgView } from "./pos_chat_view";

export class PosMsgView extends owl.Component {
    setup() {
        super.setup();
        this.root = useRef("root");
        onMounted(this.render_msg_view);
        this.MsgWindow = new ChatMsgView();
        this.state = useState({
            data: [],
        });
    }

    /** Fetch all chat messages */
    render_msg_view() {
        rpc("/pos_systray/message_data").then((data) => {
            const message_list = data.map((message) => {
                const parser = new DOMParser();
                const parsedHtml = parser.parseFromString(message.message_body, "text/html");
                const plainText = parsedHtml.documentElement.textContent;
                return {
                    id: message.id,
                    type: message.type,
                    name: message.name,
                    message_body: plainText,
                };
            });
            this.state.data = message_list;
        });
    }

    /** Toggle visibility between All, Chat, and Channels */
    toggleView(activeButtonId, activeSectionId) {
        ["all_message", "all_chat", "all_channels"].forEach((id) => {
            this.root.el.querySelector(`#${id}`).style.display = id === activeSectionId ? "block" : "none";
        });

        ["all_message_button", "all_chat_button", "all_channels_button"].forEach((id) => {
            this.root.el.querySelector(`#${id}`).style.color = id === activeButtonId ? "#000" : "#9c9a97";
        });
    }

    _onClickAllMessage() {
        this.toggleView("all_message_button", "all_message");
    }

    _onClickAllChannels() {
        this.toggleView("all_channels_button", "all_channels");
    }

    _onClickAllChat() {
        this.toggleView("all_chat_button", "all_chat");
    }

    /** Open chat view */
    _onClickToMessage(ev) {
        const channel_id = ev.currentTarget.getAttribute("value");
        this.__owl__.remove();

        if (!document.querySelector("#pos_chat_view")) {
            this.schedule_dropdown = mount(ChatMsgView, document.body, { props: { channel_id } });
        } else {
            this.schedule_dropdown = mount(ChatMsgView, document.body, { props: { channel_id } });
        }
    }
}

PosMsgView.template = xml`
    <div class="pos_systray_template" t-ref="root"
        style="height:auto;width:350px;background-color:#f3f3f3;position:fixed;right:5px;top:49px;padding:10px;margin: 7px 14px;">

        <div style="display:flex;height: 27px;">
            <p style="margin-left:10px;cursor: pointer;" id="all_message_button"
               t-on-click="_onClickAllMessage">All</p>
            <p style="margin-left:10px;cursor: pointer;color:#9c9a97;" id="all_chat_button"
               t-on-click="_onClickAllChat">Chat</p>
            <p style="margin-left:10px;cursor: pointer;color:#9c9a97;" id="all_channels_button"
               t-on-click="_onClickAllChannels">Channels</p>
        </div>

        <hr/>

        <div id="all_message">
            <t t-foreach="state.data" t-as="data" t-key="data.id">
                <div style="background-color: #e7f3fe;border-left: 6px solid #2196F3;
                margin-bottom: 15px;padding: 4px 12px;display:flex;cursor:pointer;" t-att-value="data.id"
                    t-on-click="_onClickToMessage">

                    <div style="width:30px">
                        <t t-if="data.type == 'channel'">
                            <i style="margin:40%" class="fa fa-users"/>
                        </t>
                        <t t-else="">
                            <i style="margin:40%" class="fa fa-user"/>
                        </t>
                    </div>

                    <div style="margin-left: 20px;width: 250px">
                        <span t-esc="data.name"/>
                        <br/>
                        <small style="color:#9c9a97;" t-raw="data.message_body"/>
                    </div>
                </div>
            </t>
        </div>

        <div id="all_chat" style="display:none">
            <t t-foreach="state.data" t-as="data" t-key="data.id">
                <t t-if="data.type == 'chat'">
                    <div style="background-color: #ddffdd;  border-left: 6px solid #04AA6D;
                    margin-bottom: 15px;padding: 4px 12px;display:flex;cursor:pointer;" t-att-value="data.id"
                         t-on-click="_onClickToMessage">

                        <div style="width:30px">
                            <i style="margin:8px" class="fa fa-user"/>
                        </div>

                        <div style="margin-left: 20px;width: 250px">
                            <span t-esc="data.name"/>
                            <br/>
                            <small style="color:#9c9a97;" t-raw="data.message_body"/>
                        </div>
                    </div>
                </t>
            </t>
        </div>

        <div id="all_channels" style="display:none">
            <t t-foreach="state.data" t-as="data" t-key="data.id">
                <t t-if="data.type == 'channel'">
                    <div style="background-color: #ffffcc;border-left: 6px solid #ffeb3b;
                        margin-bottom: 15px;padding: 4px 12px;display:flex;cursor:pointer;" t-att-value="data.id"
                         t-on-click="_onClickToMessage">

                        <div style="width:30px">
                            <i style="margin:8px" class="fa fa-users"/>
                        </div>

                        <div style="margin-left: 20px;width: 250px">
                            <span t-esc="data.name"/>
                            <br/>
                            <small style="color:#9c9a97;" t-raw="data.message_body"/>
                        </div>
                    </div>
                </t>
            </t>
        </div>
    </div>`;
