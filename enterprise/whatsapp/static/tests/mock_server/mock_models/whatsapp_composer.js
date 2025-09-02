import { models } from "@web/../tests/web_test_helpers";

export class WhatsAppComposer extends models.ServerModel {
    _name = "whatsapp.composer";

    _views = { [`form,false`]: `<form/>` };
}
