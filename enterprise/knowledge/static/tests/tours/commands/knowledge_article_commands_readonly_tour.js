/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { embeddedViewPatchFunctions, endKnowledgeTour } from '../knowledge_tour_utils.js';
import { EmbeddedVideoComponent } from "@html_editor/others/embedded_components/core/video/video";

import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";

//------------------------------------------------------------------------------
// UTILS
//------------------------------------------------------------------------------

const embeddedViewPatchUtil = embeddedViewPatchFunctions();

// This tour follows the 'knowledge_article_commands_tour'.
// As it contains a video, we re-use the Mock to avoid relying on actual YouTube content
let unpatchVideoEmbed;
let unpatchVideoSelector;

class MockedVideoIframe extends Component {
    static template = xml`
        <div class="o_video_iframe_src" t-out="props.src" />
    `;
    static props = ["src"];
}

const videoPatchSteps = [{ // patch the components
    trigger: "body",
    run: () => {
        unpatchVideoEmbed = patch(EmbeddedVideoComponent.components, {
            ...EmbeddedVideoComponent.components,
            VideoIframe: MockedVideoIframe
        });
        unpatchVideoSelector = patch(VideoSelector.components, {
            ...VideoSelector.components,
            VideoIframe: MockedVideoIframe
        });
    },
}];

const videoUnpatchSteps = [{ // unpatch the components
    trigger: "body",
    run: () => {
        unpatchVideoEmbed();
        unpatchVideoSelector();
    },
}];

//------------------------------------------------------------------------------
// TOUR STEPS - KNOWLEDGE COMMANDS
//------------------------------------------------------------------------------

registry.category("web_tour.tours").add("knowledge_article_commands_readonly_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            // open the Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
            run: "click",
        },
        ...videoPatchSteps,
        {
            trigger: "body",
            run() {
                embeddedViewPatchUtil.before();
            },
        },
        /*
         * EMBED VIEW: /list
         * Checks that a user that has readonly access on an article cannot create items from the item list.
         * Note: this tour follows the 'knowledge_article_commands_tour', so we re-use the list name.
         */
        {
            content: "Check view list has no add button",
            trigger: `[data-embedded="view"]:has(.o_list_view):not(:has(.o_list_button_add))`,
        },
        /*
         * EMBED VIEW: /kanban
         * Checks that a user that has readonly access on an article cannot create items from the item kanban.
         * Note: this tour follows the 'knowledge_article_commands_tour', so we re-use the kanban name.
         */
        {
            content: "Check kaban has no add button",
            trigger: `[data-embedded="view"]:has(.o_kanban_view):not(:has(.o_kanban_quick_add))`,
        },
        ...videoUnpatchSteps,
        {
            trigger: "body",
            run() {
                embeddedViewPatchUtil.after();
            },
        },
        ...endKnowledgeTour(),
    ],
});
