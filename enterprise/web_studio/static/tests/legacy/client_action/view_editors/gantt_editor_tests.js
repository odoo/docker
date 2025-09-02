import { browser } from "@web/core/browser/browser";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    createMockViewResult,
    createViewEditor,
    editAnySelect,
    registerViewEditorDependencies,
} from "@web_studio/../tests/legacy/client_action/view_editors/view_editor_tests_utils";
import { registry } from "@web/core/registry";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";

/** @type {Node} */
let target;
let serverData;

QUnit.module(
    "View Editors",
    {
        async beforeEach() {
            const staticServerData = {
                models: {
                    coucou: {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            display_name: { string: "Name", type: "char" },
                            start: { string: "Start Date", type: "datetime" },
                            stop: { string: "Stop Date", type: "datetime" },
                        },
                        records: [
                            {
                                id: 1,
                                start: "2018-11-30 18:30:00",
                                stop: "2018-12-31 18:29:59",
                            },
                        ],
                    },
                },
            };

            serverData = JSON.parse(JSON.stringify(staticServerData));

            registerViewEditorDependencies();

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            target = getFixture();
        },
    },
    function () {
        QUnit.module("Gantt");

        QUnit.test("empty gantt editor", async function (assert) {
            assert.expect(3);

            registry.category("services").add("datetime_picker", datetimePickerService);

            const arch = `<gantt date_start='start' date_stop='stop' />`;
            await createViewEditor({
                serverData,
                type: "gantt",
                resModel: "coucou",
                arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.strictEqual(
                            args.operations[0].new_attrs.precision,
                            '{"day":"hour:quarter"}',
                            "should correctly set the precision"
                        );
                        return createMockViewResult(serverData, "gantt", arch, "coucou");
                    }
                },
            });

            assert.containsOnce(
                target,
                ".o_web_studio_view_renderer .o_gantt_renderer",
                "there should be a gantt view"
            );
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_web_studio_property_precision_day .o_select_menu",
                "it should be possible to edit the day precision"
            );

            await editAnySelect(
                target,
                ".o_web_studio_property_precision_day .o_select_menu",
                "Quarter Hour"
            );
        });

        QUnit.test("only show allowed scales as default scale", async function (assert) {
            registry.category("services").add("datetime_picker", datetimePickerService);

            await createViewEditor({
                serverData,
                type: "gantt",
                resModel: "coucou",
                arch: `<gantt date_start='start' date_stop='stop' scales="day,month"/>`,
            });

            await click(target, ".o_web_studio_property_default_scale .dropdown-toggle");
            assert.deepEqual(
                Array.from(target.querySelectorAll(".o_select_menu_menu .dropdown-item")).map(
                    (e) => e.textContent
                )[("Day", "Month")]
            );
        });
    }
);
