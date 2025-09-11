import { makeKwArgs } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

function _mockWebGanttWrite(args) {
    return this.env[args.model].write(...args.args, makeKwArgs({ context: args.kwargs.context }));
}

registry.category("mock_rpc").add("web_gantt_write", _mockWebGanttWrite);
