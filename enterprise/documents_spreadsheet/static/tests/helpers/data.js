import { SpreadsheetModels, defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { defineActions, fields, models, webModels } from "@web/../tests/web_test_helpers";
import { mockJoinSpreadsheetSession } from "@spreadsheet_edition/../tests/helpers/mock_server";
import { Domain } from "@web/core/domain";

export class DocumentsDocument extends models.Model {
    _name = "documents.document";

    id = fields.Integer({ string: "ID" });
    name = fields.Char({ string: "Name" });
    spreadsheet_data = fields.Binary({ string: "Data" });
    thumbnail = fields.Binary({ string: "Thumbnail" });
    favorited_ids = fields.Many2many({ string: "Name", relation: "res.users" });
    is_favorited = fields.Boolean({ string: "Name" });
    is_multipage = fields.Boolean({ string: "Is multipage" });
    mimetype = fields.Char({ string: "Mimetype" });
    partner_id = fields.Many2one({ string: "Related partner", relation: "res.partner" });
    owner_id = fields.Many2one({ string: "Owner", relation: "res.users" });
    handler = fields.Selection({
        string: "Handler",
        selection: [
            ["spreadsheet", "Spreadsheet"],
            ["frozen_spreadsheet", "Frozen Spreadsheet"],
            ["frozen_folder", "Frozen Folder"],
        ],
    });
    previous_attachment_ids = fields.Many2many({
        string: "History",
        relation: "ir.attachment",
    });
    tag_ids = fields.Many2many({ string: "Tags", relation: "documents.tag" });
    folder_id = fields.Many2one({ string: "Folder", relation: "documents.document" });
    res_model = fields.Char({ string: "Model (technical)" });
    attachment_id = fields.Many2one({ relation: "ir.attachment" });
    active = fields.Boolean({ default: true, string: "Active" });
    activity_ids = fields.One2many({ relation: "mail.activity" });
    checksum = fields.Char({ string: "Checksum" });
    file_extension = fields.Char({ string: "File extension" });
    thumbnail_status = fields.Selection({
        string: "Thumbnail status",
        selection: [["none", "None"]],
    });
    lock_uid = fields.Many2one({ relation: "res.users" });
    message_attachment_count = fields.Integer({ string: "Message attachment count" });
    message_follower_ids = fields.One2many({ relation: "mail.followers" });
    message_ids = fields.One2many({ relation: "mail.message" });
    res_id = fields.Integer({ string: "Resource ID" });
    res_name = fields.Char({ string: "Resource Name" });
    res_model_name = fields.Char({ string: "Resource Model Name" });
    type = fields.Selection({ string: "Type", selection: [["binary", "File", "folder"]] });
    url = fields.Char({ string: "URL" });
    url_preview_image = fields.Char({ string: "URL preview image" });
    file_size = fields.Integer({ string: "File size" });
    raw = fields.Char({ string: "Raw" });
    access_token = fields.Char({ string: "Access token" });
    available_embedded_actions_ids = fields.Many2many({
        string: "Available Actions",
        // relation: "ir.actions.server",
        relation: "res.partner",
    });
    alias_id = fields.Many2one({ relation: "mail.alias" });
    alias_domain_id = fields.Many2one({ relation: "mail.alias.domain" });
    alias_name = fields.Char({ string: "Alias name" });
    alias_tag_ids = fields.Many2many({ relation: "documents.tag" });
    description = fields.Char({ string: "Attachment description" });
    last_access_date_group = fields.Selection({
        string: "Last Accessed On",
        selection: [["0_older", "1_mont", "2_week", "3_day"]],
    });

    get_spreadsheets(domain = [], args) {
        let { offset, limit } = args;
        offset = offset || 0;

        const combinedDomain = Domain.and([domain, [["handler", "=", "spreadsheet"]]]).toList();
        const records = this.env["documents.document"]
            .search_read(combinedDomain)
            .map((spreadsheet) => ({
                display_name: spreadsheet.name,
                id: spreadsheet.id,
            }));
        const sliced = records.slice(offset, limit ? offset + limit : undefined);
        return { records: sliced, total: records.length };
    }

    join_spreadsheet_session(resId, accessToken) {
        const result = mockJoinSpreadsheetSession("documents.document").call(
            this,
            resId,
            accessToken
        );
        const record = this.env["documents.document"].search_read([["id", "=", resId]])[0];
        result.is_favorited = record.is_favorited;
        result.folder_id = record.folder_id[0];
        return result;
    }

    dispatch_spreadsheet_message() {
        return false;
    }

    action_open_new_spreadsheet(route, args) {
        const spreadsheetId = this.env["documents.document"].create({
            name: "Untitled spreadsheet",
            mimetype: "application/o-spreadsheet",
            spreadsheet_data: "{}",
            handler: "spreadsheet",
        });
        return {
            type: "ir.actions.client",
            tag: "action_open_spreadsheet",
            params: {
                spreadsheet_id: spreadsheetId,
                is_new_spreadsheet: true,
            },
        };
    }

    action_open_spreadsheet(args) {
        return {
            type: "ir.actions.client",
            tag: "action_open_spreadsheet",
            params: {
                spreadsheet_id: args[0],
            },
        };
    }

    get_deletion_delay() {
        return 30;
    }

    get_document_max_upload_limit() {
        return 67000000;
    }

    /**
     * @override
     */
    search_panel_select_range(fieldName) {
        const result = super.search_panel_select_range(...arguments);
        if (fieldName === "folder_id") {
            const coModel = this.env[this._fields[fieldName].relation];
            for (const recordValues of result.values || []) {
                const [record] = coModel.browse(recordValues.id);
                for (const fName of [
                    "display_name",
                    "description",
                    "parent_folder_id",
                    "has_write_access",
                    "company_id",
                ]) {
                    recordValues[fName] ??= record[fName];
                }
            }
        }
        return result;
    }

    _records = [
        {
            id: 1,
            name: "Workspace1",
            description: "Workspace",
            folder_id: false,
            available_embedded_actions_ids: [],
            type: "folder",
            access_token: "accessTokenWorkspace1",
        },
        {
            id: 2,
            name: "My spreadsheet",
            spreadsheet_data: "{}",
            is_favorited: false,
            folder_id: 1,
            handler: "spreadsheet",
            active: true,
            access_token: "accessTokenMyspreadsheet",
        },
        {
            id: 3,
            name: "",
            spreadsheet_data: "{}",
            is_favorited: true,
            folder_id: 1,
            handler: "spreadsheet",
            active: true,
            access_token: "accessToken",
        },
    ];
}

export class DocumentsTag extends models.Model {
    _name = "documents.tag";

    facet_id = fields.Many2one({ relation: "documents.facet" });
    get_tags() {
        return [];
    }
}

export class TagsCategories extends models.Model {
    _name = "documents.facet";
}

export class DocumentsWorkflowRule extends models.Model {
    _name = "documents.workflow.rule";

    note = fields.Char({ string: "Tooltip" });
    limited_to_single_record = fields.Boolean({ string: "Limited to single record" });
    create_model = fields.Selection({
        selection: [["link.to.record", "Link to record"]],
        string: "Create",
    });
}

export class SpreadsheetTemplate extends models.Model {
    _name = "spreadsheet.template";

    name = fields.Char({ string: "Name", type: "char" });
    spreadsheet_data = fields.Binary({ string: "Spreadsheet Data" });
    thumbnail = fields.Binary({ string: "Thumbnail", type: "binary" });
    sequence = fields.Integer({ string: "Sequence", type: "integer" });

    fetch_template_data(route, args) {
        const [id] = args.args;
        const record = this.env["spreadsheet.template"].search_read([["id", "=", id]])[0];
        if (!record) {
            throw new Error(`Spreadsheet Template ${id} does not exist`);
        }
        return {
            data:
                typeof record.spreadsheet_data === "string"
                    ? JSON.parse(record.spreadsheet_data)
                    : record.spreadsheet_data,
            name: record.name,
            isReadonly: false,
        };
    }

    join_spreadsheet_session(resId, accessTokens) {
        return mockJoinSpreadsheetSession("spreadsheet.template").call(this, resId, accessTokens);
    }

    _records = [
        { id: 1, name: "Template 1", spreadsheet_data: "" },
        { id: 2, name: "Template 2", spreadsheet_data: "" },
    ];

    _views = {
        search: /* xml */ `<search><field name="name"/></search>`,
    };
}

export class IrModel extends SpreadsheetModels.IrModel {
    has_searchable_parent_relation() {
        return false;
    }
}

export class IrUIMenu extends SpreadsheetModels.IrUIMenu {
    _views = {
        search: /* xml */ `<search/>`,
        list: /* xml */ `<list/>`,
        form: /* xml */ `<form/>`,
    };
}

export class MailAlias extends models.Model {
    _name = "mail.alias";

    alias_name = fields.Char({ string: "Alias Name" });
}

export class MailAliasDomain extends models.Model {
    _name = "mail.alias.domain";

    name = fields.Char({ string: "Alias Domain Name" });
}

export class ResCompany extends webModels.ResCompany {
    document_spreadsheet_folder_id = fields.Many2one({
        relation: "documents.document",
        default: 1,
    });
}

export function defineDocumentSpreadsheetModels() {
    const SpreadsheetDocumentModels = {
        MailAlias,
        MailAliasDomain,
        DocumentsDocument,
        TagsCategories,
        DocumentsTag,
        DocumentsWorkflowRule,
        SpreadsheetTemplate,
        IrModel,
        IrUIMenu,
        ResCompany,
    };
    Object.assign(SpreadsheetModels, SpreadsheetDocumentModels);
    defineSpreadsheetModels();
}

export function defineDocumentSpreadsheetTestAction() {
    defineActions([
        {
            id: 1,
            name: "partner Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            xml_id: "spreadsheet.partner_action",
            views: [
                [false, "list"],
                [false, "pivot"],
                [false, "graph"],
                [false, "search"],
                [false, "form"],
            ],
        },
    ]);
}

export function getBasicPermissionPanelData(recordExtra) {
    const record = {
        access_internal: "view",
        access_via_link: "view",
        access_url: "http://localhost:8069/share/url/132465",
        access_ids: [],
        active: true,
        ...recordExtra,
    };
    const selections = {
        access_via_link: [
            ["view", "Viewer"],
            ["edit", "Editor"],
            ["none", "None"],
        ],
        access_internal: [
            ["view", "Viewer"],
            ["edit", "Editor"],
            ["none", "None"],
        ],
        doc_access_roles: [
            ["view", "Viewer"],
            ["edit", "Editor"],
        ],
    };
    return { record, selections };
}
