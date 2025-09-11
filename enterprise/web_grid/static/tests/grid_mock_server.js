import { makeKwArgs } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

function _mockGridUpdateCell({ args, kwargs, model }) {
    kwargs = makeKwArgs(kwargs);
    const [domain, fieldNameToUpdate, value] = args;
    const records = this.env[model].search_read(domain, [fieldNameToUpdate], kwargs);
    if (records.length > 1) {
        this.env[model].copy(records[0].id, { [fieldNameToUpdate]: value });
    } else if (records.length === 1) {
        const record = records[0];
        this.env[model].write(record.id, {
            [fieldNameToUpdate]: record[fieldNameToUpdate] + value,
        });
    } else {
        this.env[model].create({ [fieldNameToUpdate]: value }, kwargs);
    }
    return false;
}

registry.category("mock_rpc").add("grid_update_cell", _mockGridUpdateCell);
