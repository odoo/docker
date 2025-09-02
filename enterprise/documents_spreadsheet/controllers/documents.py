# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re

from odoo.http import request, route
from odoo.addons.documents.controllers.documents import ShareRoute

# ends with .osheet.json or .osheet (6).json
SPREADSHEET_RE = re.compile(r'\.osheet(\s?\(\d+\))?\.json$')

class SpreadsheetShareRoute(ShareRoute):
    def _documents_render_public_view(self, document_sudo):
        if document_sudo.handler in ("spreadsheet", "frozen_spreadsheet"):
            return self._documents_render_portal_view(document_sudo)

        return super()._documents_render_public_view(document_sudo)

    def _documents_render_portal_view(self, document):
        if document.handler not in ("spreadsheet", "frozen_spreadsheet"):
            return super()._documents_render_portal_view(document)

        # check if the spreadsheet contains "live data", if yes the rendering will fail
        if document._contains_live_data():
            return request.render("documents_spreadsheet.documents_error_live_data")

        return request.render(
            "spreadsheet.public_spreadsheet_layout",
            {
                "spreadsheet_name": document.name,
                "share": document,
                "session_info": request.env["ir.http"].session_info(),
                "props": {
                    "dataUrl": f"/documents/spreadsheet/{document.access_token}",
                    "downloadExcelUrl": f"/documents/content/{document.access_token}",
                },
            },
        )

    def _documents_content_stream(self, document_sudo):
        """
        Use the ``excel_export`` field instead of ``raw`` when
        downloading frozen spreadsheets.
        """
        if document_sudo.handler == 'frozen_spreadsheet':
            return request.env['ir.binary']._get_stream_from(document_sudo, 'excel_export')
        elif document_sudo.handler == 'spreadsheet':
            raise ValueError("non-frozen spreadsheets have no content")
        return super()._documents_content_stream(document_sudo)

    @route('/documents/spreadsheet/<access_token>', type='http', auth='public', readonly=True)
    def documents_spreadsheet(self, access_token):
        """Download the spreadsheet data for the readonly view."""
        document_sudo = self._from_access_token(access_token, skip_log=True)
        if not document_sudo:
            raise request.not_found()

        spreadsheet_data = document_sudo._get_spreadsheet_snapshot()
        spreadsheet_data['revisions'] = document_sudo._build_spreadsheet_messages()
        return json.dumps(spreadsheet_data)

    def _documents_upload_create_write(self, *args, **kwargs):
        """Set the correct handler when uploading a spreadsheet"""
        document_sudo = super()._documents_upload_create_write(*args, **kwargs)
        if (document_sudo.name
            and SPREADSHEET_RE.search(document_sudo.name)
            and document_sudo.mimetype == 'application/json'
        ):
            document_sudo.handler = 'spreadsheet'
            document_sudo._check_spreadsheet_data()
        return document_sudo
