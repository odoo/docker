import { models } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_SEARCH_ID, DEFAULT_MAIL_VIEW_ID } from "@mail/../tests/mock_server/mock_models/constants";

export class ApprovalRequest extends models.ServerModel {
    _name = "approval.request";
    _views = {
        [`search, ${DEFAULT_MAIL_SEARCH_ID}`]: /* xml */ `<search/>`,
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: /* xml */ `
            <form>
                <chatter/>
            </form>`,
    };

}
