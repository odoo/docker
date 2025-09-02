import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";


class DocumentsTypeIcon extends Component {
    static template = "documents.DocumentsTypeIcon";
    static props = { ...standardFieldProps };
}

const documentsTypeIcon = {
    component: DocumentsTypeIcon,
};

registry.category("fields").add("documents_type_icon", documentsTypeIcon);
