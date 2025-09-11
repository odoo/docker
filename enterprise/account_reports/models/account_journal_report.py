# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import datetime

from PIL import ImageFont
from markupsafe import Markup

from odoo import models, _
from odoo.tools import SQL
from odoo.tools.misc import xlsxwriter, file_path
from collections import defaultdict

XLSX_GRAY_200 = '#EEEEEE'
XLSX_BORDER_COLOR = '#B4B4B4'
XLSX_FONT_SIZE_DEFAULT = 8
XLSX_FONT_SIZE_HEADING = 11


class JournalReportCustomHandler(models.AbstractModel):
    _name = "account.journal.report.handler"
    _inherit = "account.report.custom.handler"
    _description = "Journal Report Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        """ Initialize the options for the journal report. """

        # Initialise the custom option for this report.
        options['ignore_totals_below_sections'] = True
        options['show_payment_lines'] = previous_options.get('show_payment_lines', True)

    def _get_custom_display_config(self):
        return {
            'css_custom_class': 'journal_report',
            'pdf_css_custom_class': 'journal_report_pdf',
            'components': {
                'AccountReportLine': 'account_reports.JournalReportLine',
            },
            'templates': {
                'AccountReportFilters': 'account_reports.JournalReportFilters',
                'AccountReportLineName': 'account_reports.JournalReportLineName',
            }
        }

    ##########################################################################
    # UI
    ##########################################################################

    def _report_custom_engine_journal_report(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):

        def build_result_dict(current_groupby, query_line):
            """
            Creates a line entry used by the custom engine
            """
            if current_groupby == 'account_id':
                code = query_line['account_code'][0]
            elif current_groupby == 'journal_id':
                code = query_line['journal_code'][0]
            else:
                code = None

            result_line_dict = {
                'code': code,
                'credit': query_line['credit'],
                'debit': query_line['debit'],
                'balance': query_line['balance'] if current_groupby == 'account_id' else None
            }
            return query_line['grouping_key'], result_line_dict

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        # If it is the first line, we want to render our column label
        # Since we don't use the one from the base report
        if not current_groupby:
            return {
                'code': None,
                'debit': None,
                'credit': None,
                'balance': None
            }

        query = report._get_report_query(options, 'strict_range')
        account_alias = query.join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
        account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)

        groupby_clause = SQL.identifier('account_move_line', current_groupby)
        select_from_groupby = SQL('%s AS grouping_key', groupby_clause)

        query = SQL(
            """
                SELECT
                    %(select_from_groupby)s,
                    ARRAY_AGG(DISTINCT %(account_code)s) AS account_code,
                    ARRAY_AGG(DISTINCT j.code) AS journal_code,
                    SUM("account_move_line".debit) AS debit,
                    SUM("account_move_line".credit) AS credit,
                    SUM("account_move_line".balance) AS balance
                FROM %(table)s
                JOIN account_move am ON am.id = account_move_line.move_id
                JOIN account_journal j ON j.id = am.journal_id
                JOIN res_company cp ON cp.id = am.company_id
                WHERE %(case_statement)s AND %(search_conditions)s
                GROUP BY %(groupby_clause)s
                ORDER BY %(groupby_clause)s
            """,
            select_from_groupby=select_from_groupby,
            account_code=account_code,
            table=query.from_clause,
            search_conditions=query.where_clause,
            case_statement=self._get_payment_lines_filter_case_statement(options),
            groupby_clause=groupby_clause
        )
        self._cr.execute(query)
        query_lines = self._cr.dictfetchall()
        result_lines = []

        for query_line in query_lines:
            result_lines.append(build_result_dict(current_groupby, query_line))

        return result_lines

    def _custom_line_postprocessor(self, report, options, lines):
        """
        Process the lines generated by the engine to add metadata and add the tax summary lines
        """
        new_lines = []

        for i, line in enumerate(lines):
            new_lines.append(line)
            line_id = line['id']

            line_model, res_id = report._get_model_info_from_id(line_id)
            if line_model == 'account.journal':
                line['journal_id'] = res_id
            elif line_model == 'account.account':
                res_ids_map = report._get_res_ids_from_line_id(line_id, ['account.journal', 'account.account'])
                line['journal_id'] = res_ids_map['account.journal']
                line['account_id'] = res_ids_map['account.account']
                line['date'] = options['date']

                journal = self.env['account.journal'].browse(line['journal_id'])

                # If it is the last line of the journal section
                # Check if the journal has taxes and if so, add the tax summaries
                if (i + 1 == len(lines) or (i + 1 < len(lines) and report._get_model_info_from_id(lines[i + 1]['id'])[0] != 'account.account')) and self._section_has_tax(options, journal.id):
                    tax_summary_line = {
                        'id': report._get_generic_line_id(False, False, parent_line_id=line['parent_id'], markup='tax_report_section'),
                        'name': '',
                        'parent_id': line['parent_id'],
                        'journal_id': journal.id,
                        'is_tax_section_line': True,
                        'columns': [],
                        'colspan': len(options['columns']) + 1,
                        'level': 4,
                        **self._get_tax_summary_section(options, {'id': journal.id, 'type': journal.type})
                    }
                    new_lines.append(tax_summary_line)

        # If we render the first level it means that we need to render
        # the global tax summary lines
        if report._get_model_info_from_id(lines[0]['id'])[0] == 'account.report.line':
            if self._section_has_tax(options, False):
                # We only add the global summary line if it has taxes
                new_lines.append({
                        'id': report._get_generic_line_id(False, False, markup='tax_report_section_heading'),
                        'name': _('Global Tax Summary'),
                        'level': 0,
                        'columns': [],
                        'unfoldable': False,
                        'colspan': len(options['columns']) + 1
                        # We want it to take the whole line. It makes it easier to unfold it.
                    })
                summary_line = {
                    'id': report._get_generic_line_id(False, False, markup='tax_report_section'),
                    'name': '',
                    'is_tax_section_line': True,
                    'columns': [],
                    'colspan': len(options['columns']) + 1,
                    'level': 4,
                    'class': 'o_account_reports_ja_subtable',
                    **self._get_tax_summary_section(options)
                }
                new_lines.append(summary_line)

        return new_lines

    ##########################################################################
    # PDF Export
    ##########################################################################

    def export_to_pdf(self, options):
        """
        Overrides the default export_to_pdf function from account.report to
        not use the default lines system since we make a different report
        from the UI
        """
        report = self.env['account.report'].browse(options['report_id'])
        base_url = report.get_base_url()
        print_options = {
            **report.get_options(previous_options={**options, 'export_mode': 'print'}),
            'css_custom_class': self._get_custom_display_config().get('pdf_css_custom_class', 'journal_report_pdf')
        }
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        footer = self.env['ir.actions.report']._render_template('account_reports.internal_layout', values=rcontext)
        footer = self.env['ir.actions.report']._render_template('web.minimal_layout', values=dict(rcontext, subst=True, body=Markup(footer.decode())))

        document_data = self._generate_document_data_for_export(report, print_options, 'pdf')
        render_values = {
            'report': report,
            'options': print_options,
            'base_url': base_url,
            'document_data': document_data
        }
        body = self.env['ir.qweb']._render('account_reports.journal_report_pdf_export_main', render_values)

        action_report = self.env['ir.actions.report']
        pdf_file_stream = io.BytesIO(action_report._run_wkhtmltopdf(
            [body],
            footer=footer.decode(),
            landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
                'data-report-margin-bottom': 15,
            }
        ))

        pdf_result = pdf_file_stream.getvalue()
        pdf_file_stream.close()

        return {
            'file_name': report.get_default_report_filename(print_options, 'pdf'),
            'file_content': pdf_result,
            'file_type': 'pdf',
        }

    ##########################################################################
    # XLSX Export
    ##########################################################################

    def export_to_xlsx(self, options, response=None):
        """
        Overrides the default XLSX Generation from account.repor to use a custom one.
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        report = self.env['account.report'].search([('id', '=', options['report_id'])], limit=1)
        print_options = report.get_options(previous_options={**options, 'export_mode': 'print'})
        document_data = self._generate_document_data_for_export(report, print_options, 'xlsx')

        # We need to use fonts to calculate column width otherwise column width would be ugly
        # Using Lato as reference font is a hack and is not recommended. Customer computers don't have this font by default and so
        # the generated xlsx wouldn't have this font. Since it is not by default, we preferred using Arial font as default and keep
        # Lato as reference for columns width calculations.
        fonts = {}
        for font_size in (XLSX_FONT_SIZE_HEADING, XLSX_FONT_SIZE_DEFAULT):
            fonts[font_size] = defaultdict()
            for font_type in ('Reg', 'Bol', 'RegIta', 'BolIta'):
                try:
                    lato_path = f'web/static/fonts/lato/Lato-{font_type}-webfont.ttf'
                    fonts[font_size][font_type] = ImageFont.truetype(file_path(lato_path), font_size)
                except (OSError, FileNotFoundError):
                    # This won't give great result, but it will work.
                    fonts[font_size][font_type] = ImageFont.load_default()

        for journal_vals in document_data['journals_vals']:
            cursor_x = 0
            cursor_y = 0

            # Default sheet properties
            sheet = workbook.add_worksheet(journal_vals['name'][:31])
            columns = journal_vals['columns']

            for column in columns:
                align = 'left'
                if 'o_right_alignment' in column.get('class', ''):
                    align = 'right'
                self._write_cell(cursor_x, cursor_y, column['name'], 1, False, report, fonts, workbook, sheet, XLSX_FONT_SIZE_HEADING,
                                 True, XLSX_GRAY_200, align, 2, 2)
                cursor_x = cursor_x + 1

            # Set cursor coordinates for the table generation
            cursor_y += 1
            cursor_x = 0
            for line in journal_vals['lines'][:-1]:
                is_first_aml_line = False
                for column in columns:
                    border_top = 0 if not is_first_aml_line else 1
                    align = 'left'

                    if line.get(column['label'], {}).get('data'):
                        data = line[column['label']]['data']
                        is_date = isinstance(data, datetime.date)
                        bold = False

                        if 'o_right_alignment' in column.get('class', ''):
                            align = 'right'

                        if line[column['label']].get('class') and 'o_bold' in line[column['label']]['class']:
                            # if the cell has bold styling, should only be on the first line of each aml
                            is_first_aml_line = True
                            border_top = 1
                            bold = True

                        self._write_cell(cursor_x, cursor_y, data, 1, is_date, report, fonts, workbook, sheet, XLSX_FONT_SIZE_DEFAULT,
                                         bold, 'white', align, 0, border_top, XLSX_BORDER_COLOR)

                    else:
                        # Empty value
                        self._write_cell(cursor_x, cursor_y, '', 1, False, report, fonts, workbook, sheet, XLSX_FONT_SIZE_DEFAULT, False,
                                         'white', align, 0, border_top, XLSX_BORDER_COLOR)

                    cursor_x += 1
                cursor_x = 0
                cursor_y += 1

            # Draw total line
            total_line = journal_vals['lines'][-1]
            for column in columns:
                data = ''
                align = 'left'

                if total_line.get(column['label'], {}).get('data'):
                    data = total_line[column['label']]['data']

                if 'o_right_alignment' in column.get('class', ''):
                    align = 'right'

                self._write_cell(cursor_x, cursor_y, data, 1, False, report, fonts, workbook, sheet, XLSX_FONT_SIZE_DEFAULT, True,
                                 XLSX_GRAY_200, align, 2, 2)
                cursor_x += 1

            cursor_x = 0

            sheet.set_default_row(20)
            sheet.set_row(0, 30)

            # Tax tables drawing
            if journal_vals.get('tax_summary'):
                self._write_tax_summaries_to_sheet(report, workbook, sheet, fonts, len(columns) + 1, 1, journal_vals['tax_summary'])

        if document_data.get('global_tax_summary'):
            self._write_tax_summaries_to_sheet(
                report,
                workbook,
                workbook.add_worksheet(_('Global Tax Summary')[:31]),
                fonts,
                0,
                0,
                document_data['global_tax_summary']
            )

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': report.get_default_report_filename(options, 'xlsx'),
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    def _write_cell(self, x, y, value, colspan, datetime, report, fonts, workbook, sheet, font_size, bold=False,
                    bg_color='white', align='left', border_bottom=0, border_top=0, border_color='0x000000'):
        """
        Write a value to a specific cell in the sheet with specific styling

        This helps to not create style format for every use case

        :param x:               The x coordinate of the cell to write in
        :param y:               The y coordinate of the cell to write in
        :param value:           The value to write
        :param colspan:         The number of columns to extend
        :param datetime:        True if the value is a date else False
        :param report:          The current report
        :param fonts:           The fonts used to calculate the size of each cells. We use Lato because we cannot get Arial but, we write in Arial since we cannot embed Lato on the worksheet
        :param workbook:        The workbook currently using
        :param sheet:           The sheet from the workbook to write on
        :param font_size:       The font size to write with
        :param bold:            True if the written value should be bold default: False
        :param bg_color:        The background color of the cell in hex or string ex: '#fff' default: 'white'
        :param align:           The alignement of the text ex: 'left', 'right', 'center' default: 'left'
        :param border_bottom:   The width of the bottom border default: 0
        :param border_top:      The width of the top border default: 0
        :param border_color:    The color of the borders in hex or string default: '0x000'
        """
        style = workbook.add_format({
            'font_name': 'Arial',
            'font_size': font_size,
            'bold': bold,
            'bg_color': bg_color,
            'align': align,
            'bottom': border_bottom,
            'top': border_top,
            'border_color': border_color,
        })

        if colspan == 1:
            if datetime:
                style.set_num_format('yyyy-mm-dd')
                sheet.write_datetime(y, x, value, style)
            else:
                # Some account_move_lines cells can have multiple lines: one for the title then some additional lines for text.
                # On Xlsx it's better to keep everything on one line so when you click on cell, all the value is shown and not juste the title
                if isinstance(value, str):
                    value = value.replace('\n', ' ')
                report._set_xlsx_cell_sizes(sheet, fonts[font_size], x, y, value, style, colspan > 1)
                sheet.write(y, x, value, style)
        else:
            sheet.merge_range(y, x, y, x + colspan - 1, value, style)

    def _write_tax_summaries_to_sheet(self, report, workbook, sheet, fonts, start_x, start_y, tax_summary):
        cursor_x = start_x
        cursor_y = start_y

        # Tax applied
        columns = []
        taxes = tax_summary.get('tax_report_lines')
        if taxes:
            start_align_right = start_x + 1

            if len(taxes) > 1:
                start_align_right += 1
                columns.append(_('Country'))

            columns += [_('Name'), _('Base Amount'), _('Tax Amount')]
            if tax_summary.get('tax_non_deductible_column'):
                columns.append(_('Non-Deductible'))
            if tax_summary.get('tax_deductible_column'):
                columns.append(_('Deductible'))
            if tax_summary.get('tax_due_column'):
                columns.append(_('Due'))

            # Draw Tax Applied Table
            # Write tax applied header amd columns
            self._write_cell(cursor_x, cursor_y, _('Taxes Applied'), len(columns), False, report, fonts, workbook, sheet,
                             XLSX_FONT_SIZE_HEADING, True, 'white', 'left', 2)
            cursor_y += 1
            for column in columns:
                align = 'left'
                if cursor_x >= start_align_right:
                    align = 'right'
                self._write_cell(cursor_x, cursor_y, column, 1, False, report, fonts, workbook, sheet, XLSX_FONT_SIZE_DEFAULT, True,
                                 XLSX_GRAY_200, align, 2)
                cursor_x += 1

            cursor_x = start_x
            cursor_y += 1

            for country in taxes:
                is_country_first_line = True
                for tax in taxes[country]:
                    if len(taxes) > 1:
                        if is_country_first_line:
                            is_country_first_line = not is_country_first_line
                            self._write_cell(cursor_x, cursor_y, country, 1, False, report, fonts, workbook, sheet,
                                             XLSX_FONT_SIZE_DEFAULT, True, 'white', 'left', 1, 0, XLSX_BORDER_COLOR)

                        cursor_x += 1

                    self._write_cell(cursor_x, cursor_y, tax['name'], 1, False, report, fonts, workbook, sheet, XLSX_FONT_SIZE_DEFAULT,
                                     True, 'white', 'left', 1, 0, XLSX_BORDER_COLOR)
                    self._write_cell(cursor_x + 1, cursor_y, tax['base_amount'], 1, False, report, fonts, workbook, sheet,
                                     XLSX_FONT_SIZE_DEFAULT, False, 'white', 'right', 1, 0, XLSX_BORDER_COLOR)
                    self._write_cell(cursor_x + 2, cursor_y, tax['tax_amount'], 1, False, report, fonts, workbook, sheet,
                                     XLSX_FONT_SIZE_DEFAULT, False, 'white', 'right', 1, 0, XLSX_BORDER_COLOR)
                    cursor_x += 3

                    if tax_summary.get('tax_non_deductible_column'):
                        self._write_cell(cursor_x, cursor_y, tax['tax_non_deductible'], 1, False, report, fonts, workbook, sheet,
                                         XLSX_FONT_SIZE_DEFAULT, False, 'white', 'right', 1, 0, XLSX_BORDER_COLOR)
                        cursor_x += 1

                    if tax_summary.get('tax_deductible_column'):
                        self._write_cell(cursor_x, cursor_y, tax['tax_deductible'], 1, False, report, fonts, workbook, sheet,
                                         XLSX_FONT_SIZE_DEFAULT, False, 'white', 'right', 1, 0, XLSX_BORDER_COLOR)
                        cursor_x += 1

                    if tax_summary.get('tax_due_column'):
                        self._write_cell(cursor_x, cursor_y, tax['tax_due'], 1, False, report, fonts, workbook, sheet,
                                         XLSX_FONT_SIZE_DEFAULT, False, 'white', 'right', 1, 0, XLSX_BORDER_COLOR)

                    cursor_x = start_x
                    cursor_y += 1

        cursor_x = start_x
        cursor_y += 2

        # Tax grids
        columns = []
        grids = tax_summary.get('tax_grid_summary_lines')
        if grids:
            start_align_right = start_x + 1
            if len(grids) > 1:
                start_align_right += 1
                columns.append(_('Country'))

            columns += [_('Grid'), _('+'), _('-'), _('Impact On Grid')]

            # Draw Tax Applied Table
            # Write tax applied columns and header
            self._write_cell(cursor_x, cursor_y, _('Impact On Grid'), len(columns), False, report, fonts, workbook, sheet,
                             XLSX_FONT_SIZE_HEADING, True, 'white', 'left', 2)

            cursor_y += 1
            for column in columns:
                align = 'left'
                if cursor_x >= start_align_right:
                    align = 'right'
                self._write_cell(cursor_x, cursor_y, column, 1, False, report, fonts, workbook, sheet, XLSX_FONT_SIZE_DEFAULT, True,
                                 XLSX_GRAY_200, align, 2)
                cursor_x += 1

            cursor_x = start_x
            cursor_y += 1

            for country in grids:
                is_country_first_line = True
                for grid_name in grids[country]:
                    if len(grids) > 1:
                        if is_country_first_line:
                            is_country_first_line = not is_country_first_line
                            self._write_cell(cursor_x, cursor_y, country, 1, False, report, fonts, workbook, sheet, XLSX_FONT_SIZE_DEFAULT,
                                            True, 'white', 'left', 1, 0, XLSX_BORDER_COLOR)

                        cursor_x += 1

                    self._write_cell(cursor_x, cursor_y, grid_name, 1, False, report, fonts, workbook, sheet, XLSX_FONT_SIZE_DEFAULT, True,
                                     'white', 'left', 1, 0, XLSX_BORDER_COLOR)
                    self._write_cell(cursor_x + 1, cursor_y, grids[country][grid_name].get('+', 0), 1, False, report, fonts, workbook,
                                     sheet, XLSX_FONT_SIZE_DEFAULT, False, 'white', 'right', 1, 0, XLSX_BORDER_COLOR)
                    self._write_cell(cursor_x + 2, cursor_y, grids[country][grid_name].get('-', 0), 1, False, report, fonts, workbook,
                                     sheet, XLSX_FONT_SIZE_DEFAULT, False, 'white', 'right', 1, 0, XLSX_BORDER_COLOR)
                    self._write_cell(cursor_x + 3, cursor_y, grids[country][grid_name]['impact'], 1, False, report, fonts, workbook,
                                     sheet, XLSX_FONT_SIZE_DEFAULT, False, 'white', 'right', 1, 0, XLSX_BORDER_COLOR)

                    cursor_x = start_x
                    cursor_y += 1

    ##########################################################################
    # Document Data Generation
    ##########################################################################

    def _generate_document_data_for_export(self, report, options, export_type='pdf'):
        """
        Used to generate all the data needed for the rendering of the export

        :param export_type:     The export type the generation need to use can be ('pdf' or 'xslx')

        :return: a dictionnary containing a list of all lines grouped by journals and a dictionnay with the global tax summary lines
        - journals_vals (mandatory):                    List of dictionary containing all the lines, columns, and tax summaries
            - lines (mandatory):                        A list of dict containing all tha data for each lines in format returned by _get_lines_for_journal
            - columns (mandatory):                      A list of columns for this journal returned in the format returned by _get_columns_for_journal
            - tax_summary (optional):                   A dict of data for the tax summaries inside journals in the format returned by _get_tax_summary_section
        - global_tax_summary:                           A dict with the global tax summaries data in the format returned by _get_tax_summary_section
        """
        # Ensure that all the data is synchronized with the database before we read it
        self.env.flush_all()
        query = report._get_report_query(options, 'strict_range')
        account_alias = query.join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
        account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
        account_name = self.env['account.account']._field_to_sql(account_alias, 'name')

        query = SQL(
            """
            SELECT
                account_move_line.id AS move_line_id,
                account_move_line.name,
                account_move_line.date,
                account_move_line.invoice_date,
                account_move_line.amount_currency,
                account_move_line.tax_base_amount,
                account_move_line.currency_id AS move_line_currency,
                am.id AS move_id,
                am.name AS move_name,
                am.journal_id,
                am.currency_id AS move_currency,
                am.amount_total_in_currency_signed AS amount_currency_total,
                am.currency_id != cp.currency_id AS is_multicurrency,
                p.name AS partner_name,
                %(account_code)s AS account_code,
                %(account_name)s AS account_name,
                %(account_alias)s.account_type AS account_type,
                COALESCE(account_move_line.debit, 0) AS debit,
                COALESCE(account_move_line.credit, 0) AS credit,
                COALESCE(account_move_line.balance, 0) AS balance,
                %(j_name)s AS journal_name,
                j.code AS journal_code,
                j.type AS journal_type,
                cp.currency_id AS company_currency,
                CASE WHEN j.type = 'sale' THEN am.payment_reference WHEN j.type = 'purchase' THEN am.ref END AS reference,
                array_remove(array_agg(DISTINCT %(tax_name)s), NULL) AS taxes,
                array_remove(array_agg(DISTINCT %(tag_name)s), NULL) AS tax_grids
            FROM %(table)s
            JOIN account_move am ON am.id = account_move_line.move_id
            LEFT JOIN res_partner p ON p.id = account_move_line.partner_id
            JOIN account_journal j ON j.id = am.journal_id
            JOIN res_company cp ON cp.id = am.company_id
            LEFT JOIN account_move_line_account_tax_rel aml_at_rel ON aml_at_rel.account_move_line_id = account_move_line.id
            LEFT JOIN account_tax parent_tax ON parent_tax.id = aml_at_rel.account_tax_id and parent_tax.amount_type = 'group'
            LEFT JOIN account_tax_filiation_rel tax_filiation_rel ON tax_filiation_rel.parent_tax = parent_tax.id
            LEFT JOIN account_tax tax ON (tax.id = aml_at_rel.account_tax_id and tax.amount_type != 'group') or tax.id = tax_filiation_rel.child_tax
            LEFT JOIN account_account_tag_account_move_line_rel tag_rel ON tag_rel.account_move_line_id = account_move_line.id
            LEFT JOIN account_account_tag tag ON tag_rel.account_account_tag_id = tag.id
            LEFT JOIN res_currency journal_curr ON journal_curr.id = j.currency_id
            WHERE %(case_statement)s AND %(search_conditions)s
            GROUP BY "account_move_line".id, am.id, p.id, %(account_alias)s.id, j.id, cp.id, journal_curr.id, account_code, account_name
            ORDER BY
                CASE j.type
                    WHEN 'sale' THEN 1
                    WHEN 'purchase' THEN 2
                    WHEN 'general' THEN 3
                    WHEN 'bank' THEN 4
                    ELSE 5
                END,
                j.sequence,
                CASE WHEN am.name = '/' THEN 1 ELSE 0 END, am.date, am.name,
                CASE %(account_alias)s.account_type
                    WHEN 'liability_payable' THEN 1
                    WHEN 'asset_receivable' THEN 1
                    WHEN 'liability_credit_card' THEN 5
                    WHEN 'asset_cash' THEN 5
                    ELSE 2
                END,
                account_move_line.tax_line_id NULLS FIRST
            """,
            table=query.from_clause,
            case_statement=self._get_payment_lines_filter_case_statement(options),
            search_conditions=query.where_clause,
            account_code=account_code,
            account_name=account_name,
            account_alias=SQL.identifier(account_alias),
            j_name=self.env['account.journal']._field_to_sql('j', 'name'),
            tax_name=self.env['account.tax']._field_to_sql('tax', 'name'),
            tag_name=self.env['account.account.tag']._field_to_sql('tag', 'name')
        )

        self._cr.execute(query)
        result = {}

        # Grouping by journal_id then move_id
        for entry in self._cr.dictfetchall():
            result.setdefault(entry['journal_id'], {})
            result[entry['journal_id']].setdefault(entry['move_id'], [])
            result[entry['journal_id']][entry['move_id']].append(entry)

        journals_vals = []
        any_journal_group_has_taxes = False

        for journal_entry_dict in result.values():
            account_move_vals_list = list(journal_entry_dict.values())
            journal_vals = {
                'id': account_move_vals_list[0][0]['journal_id'],
                'name': account_move_vals_list[0][0]['journal_name'],
                'code': account_move_vals_list[0][0]['journal_code'],
                'type': account_move_vals_list[0][0]['journal_type']
            }

            if self._section_has_tax(options, journal_vals['id']):
                journal_vals['tax_summary'] = self._get_tax_summary_section(options, journal_vals)
                any_journal_group_has_taxes = True

            journal_vals['lines'] = self._get_export_lines_for_journal(report, options, export_type, journal_vals, account_move_vals_list)
            journal_vals['columns'] = self._get_columns_for_journal(journal_vals, export_type)
            journals_vals.append(journal_vals)

        return {
            'journals_vals': journals_vals,
            'global_tax_summary': self._get_tax_summary_section(options) if any_journal_group_has_taxes else False
        }

    def _get_columns_for_journal(self, journal, export_type='pdf'):
        """
        Creates a columns list that will be used in this journal for the pdf report

        :return: A list of the columns as dict each having:
            - name (mandatory):     A string that will be displayed
            - label (mandatory):    A string used to link lines with the column
            - class (optional):     A string with css classes that need to be applied to all that column
        """
        columns = [
            {'name': _('Document'), 'label': 'document'},
        ]

        # We have different columns regarding we are exporting to a PDF file or an XLSX document
        if export_type == 'pdf':
            columns.append({'name': _('Account'), 'label': 'account_label'})
        else:
            columns.extend([
                {'name': _('Account Code'), 'label': 'account_code'},
                {'name': _('Account Label'), 'label': 'account_label'}
            ])

        columns.extend([
            {'name': _('Name'), 'label': 'name'},
            {'name': _('Debit'), 'label': 'debit', 'class': 'o_right_alignment '},
            {'name': _('Credit'), 'label': 'credit', 'class': 'o_right_alignment '},
        ])

        if journal.get('tax_summary'):
            columns.append(
                {'name': _('Taxes'), 'label': 'taxes'},
            )
            if journal['tax_summary'].get('tax_grid_summary_lines'):
                columns.append({'name': _('Tax Grids'), 'label': 'tax_grids'})

        if journal['type'] == 'bank':
            columns.append({
                'name': _('Balance'),
                'label': 'balance',
                'class': 'o_right_alignment '
            })

            if journal.get('multicurrency_column'):
                columns.append({
                    'name': _('Amount Currency'),
                    'label': 'amount_currency',
                    'class': 'o_right_alignment '
                })

        return columns

    def _get_export_lines_for_journal(self, report, options, export_type, journal_vals, account_move_vals_list):
        """
        Default document lines generation it will generate a list of lines in a format valid for the pdf and xlsx

        If it is a bank journal it will be redirected to _get_lines_for_bank_journal since this type of journals
        require more complexity
        We want to be as lightweight as possible and not at unnecessary calculations

        :return: A list of lines. Each line is a dict having:
            - 'column_label':           A dict containing the values for a cell with a key that links to the label of a column
                - data (mandatory):     The formatted cell value
                - class (optional):     Additional css classes to apply to the current cell
            - line_class (optional):    Additional css classes that applies to the entire line
        """
        lines = []

        if journal_vals['type'] == 'bank':
            return self._get_export_lines_for_bank_journal(report, options, export_type, journal_vals, account_move_vals_list)

        total_credit = 0
        total_debit = 0

        for i, account_move_line_vals_list in enumerate(account_move_vals_list):
            for j, move_line_entry_vals in enumerate(account_move_line_vals_list):
                document = False
                if j == 0:
                    document = move_line_entry_vals['move_name']
                elif j == 1:
                    document = move_line_entry_vals['date']

                line = self._get_base_line(report, options, export_type, document, move_line_entry_vals, j, i % 2 != 0, journal_vals.get('tax_summary'))

                total_credit += move_line_entry_vals['credit']
                total_debit += move_line_entry_vals['debit']

                lines.append(line)

            # Add other currency amout if this move is using multiple currencies
            move_vals_entry = account_move_line_vals_list[0]
            if move_vals_entry['is_multicurrency']:
                amount_currency_name = _(
                    'Amount in currency: %s',
                    report._format_value(
                        options,
                        move_vals_entry['amount_currency_total'],
                        'monetary',
                        format_params={'currency_id': move_vals_entry['move_currency']},
                    ),
                )
                if len(account_move_line_vals_list) <= 2:
                    lines.append({
                        'document': {'data': amount_currency_name},
                        'line_class': 'o_even ' if i % 2 == 0 else 'o_odd ',
                        'amount': {'data': move_vals_entry['amount_currency_total']},
                        'currency_id': {'data': move_vals_entry['move_currency']}
                    })
                else:
                    lines[-1]['document'] = {'data': amount_currency_name}
                    lines[-1]['amount'] = {'data': move_vals_entry['amount_currency_total']}
                    lines[-1]['currency_id'] = {'data': move_vals_entry['move_currency']}

        # Add an empty line to add a separation between the total section and the data section
        lines.append({})

        total_line = {
            'name': {'data': _('Total')},
            'debit': {'data': report._format_value(options, total_debit, 'monetary')},
            'credit': {'data': report._format_value(options, total_credit, 'monetary')},
        }

        lines.append(total_line)

        return lines

    def _get_export_lines_for_bank_journal(self, report, options, export_type, journal_vals, account_moves_vals_list):
        """
        Bank journals are more complex and should be calculated separately from other journal types

        :return: A list of lines. Each line is a dict having:
            - 'column_label':           A dict containing the values for a cell with a key that links to the label of a column
                - data (mandatory):     The formatted cell value
                - class (optional):     Additional css classes to apply to the current cell
            - line_class (optional):    Additional css classes that applies to the entire line
        """
        lines = []

        # Initial balance
        current_balance = self._query_bank_journal_initial_balance(options, journal_vals['id'])
        lines.append({
            'name': {'data': _('Starting Balance')},
            'balance': {'data': report._format_value(options, current_balance, 'monetary')},
        })

        # Debit and credit accumulators
        total_credit = 0
        total_debit = 0

        for i, account_move_line_vals_list in enumerate(account_moves_vals_list):
            is_unreconciled_payment = not any(
                line for line in account_move_line_vals_list if line['account_type'] in ('liability_credit_card', 'asset_cash')
            )

            for j, move_line_entry_vals in enumerate(account_move_line_vals_list):
                # Do not display bank account lines for bank journals
                if move_line_entry_vals['account_type'] not in ('liability_credit_card', 'asset_cash'):
                    document = ''
                    if j == 0:
                        document = f'{move_line_entry_vals["move_name"]} ({move_line_entry_vals["date"]})'
                    line = self._get_base_line(report, options, export_type, document, move_line_entry_vals, j, i % 2 != 0, journal_vals.get('tax_summary'))

                    total_credit += move_line_entry_vals['credit']
                    total_debit += move_line_entry_vals['debit']

                    if not is_unreconciled_payment:
                        # We need to invert the balance since it is a bank journal
                        line_balance = -move_line_entry_vals['balance']
                        current_balance += line_balance
                        line.update({
                            'balance': {
                                'data': report._format_value(options, current_balance, 'monetary'),
                                'class': 'o_muted ' if self.env.company.currency_id.is_zero(line_balance) else ''
                            },
                        })

                    if self.env.user.has_group('base.group_multi_currency') and move_line_entry_vals['move_line_currency'] != move_line_entry_vals['company_currency']:
                        journal_vals['multicurrency_column'] = True
                        amount_currency = -move_line_entry_vals['amount_currency'] if not is_unreconciled_payment else move_line_entry_vals['amount_currency']
                        move_line_currency = self.env['res.currency'].browse(move_line_entry_vals['move_line_currency'])
                        line.update({
                            'amount_currency': {
                                'data': report._format_value(
                                    options,
                                    amount_currency,
                                    'monetary',
                                    format_params={'currency_id': move_line_currency.id},
                                ),
                                'class': 'o_muted ' if move_line_currency.is_zero(amount_currency) else '',
                            }
                        })
                    lines.append(line)

        # Add an empty line to add a separation between the total section and the data section
        lines.append({})

        total_line = {
            'name': {'data': _('Total')},
            'balance': {'data': report._format_value(options, current_balance, 'monetary')},
        }
        lines.append(total_line)

        return lines

    def _get_base_line(self, report, options, export_type, document, line_entry, line_index, even, has_taxes):
        """
        Returns the generic part of a line that is used by both '_get_lines_for_journal' and '_get_lines_for_bank_journal'

        :return:                                    A dict with base values for the line
            - line_class (mandatory):                   Css classes that applies to this whole line
            - document (mandatory):                     A dict containing the cell data for the column document
                - data (mandatory):                         The value of the cell formatted
                - class (mandatory):                        css class for this cell
            - account (mandatory):                      A dict containing the cell data for the column account
                - data (mandatory):                         The value of the cell formatted
            - account_code (mandatory):                 A dict containing the cell data for the column account_code
                - data (mandatory):                         The value of the cell formatted
            - account_label (mandatory):                A dict containing the cell data for the column account_label
                - data (mandatory):                         The value of the cell formatted
            - name (mandatory):                         A dict containing the cell data for the column name
                - data (mandatory):                         The value of the cell formatted
            - debit (mandatory):                        A dict containing the cell data for the column debit
                - data (mandatory):                         The value of the cell formatted
                - class (mandatory):                        css class for this cell
            - credit (mandatory):                       A dict containing the cell data for the column credit
                - data (mandatory):                         The value of the cell formatted
                - class (mandatory):                        css class for this cell

            - taxes(optional):                          A dict containing the cell data for the column taxes
                - data (mandatory):                         The value of the cell formatted
            - tax_grids(optional):                          A dict containing the cell data for the column taxes
                - data (mandatory):                         The value of the cell formatted
        """
        company_currency = self.env.company.currency_id

        name = line_entry['name'] or line_entry['reference']
        account_label = line_entry['partner_name'] or line_entry['account_name']
        if line_entry['partner_name'] and line_entry['account_type'] == 'asset_receivable':
            formatted_account_label = _('AR %s', account_label)  # AR="Account Receivable"
        elif line_entry['partner_name'] and line_entry['account_type'] == 'liability_payable':
            formatted_account_label = _('AP %s', account_label)  # AP="Account Payable"
        else:
            account_label = line_entry['account_name']
            formatted_account_label = _('G %s', line_entry["account_code"])  # G="General"

        line = {
            'line_class': 'o_even ' if even else 'o_odd ',
            'document': {'data': document, 'class': 'o_bold ' if line_index == 0 else ''},
            'account_code': {'data': line_entry['account_code']},
            'account_label': {'data': account_label if export_type != 'pdf' else formatted_account_label},
            'name': {'data': name},
            'debit': {
                'data': report._format_value(options, line_entry['debit'], 'monetary'),
                'class': 'o_muted ' if company_currency.is_zero(line_entry['debit']) else ''
            },
            'credit': {
                'data': report._format_value(options, line_entry['credit'], 'monetary'),
                'class': 'o_muted ' if company_currency.is_zero(line_entry['credit']) else ''
            },
        }

        if has_taxes:
            tax_val = ''
            if line_entry['taxes']:
                tax_val = _('T: %s', ', '.join(line_entry['taxes']))
            elif line_entry['tax_base_amount'] is not None:
                tax_val = _('B: %s', report._format_value(options, line_entry['tax_base_amount'], 'monetary'))

            line.update({
                'taxes': {'data': tax_val},
                'tax_grids': {'data': ', '.join(line_entry['tax_grids'])},
            })

        return line

    ##########################################################################
    # Queries
    ##########################################################################

    def _get_payment_lines_filter_case_statement(self, options):
        if not options.get('show_payment_lines'):
            return SQL(
                """
                    (j.type != 'bank' OR EXISTS(
                        SELECT
                            1
                        FROM account_move_line
                        JOIN account_account acc ON acc.id = account_move_line.account_id
                        WHERE account_move_line.move_id = am.id
                        AND acc.account_type IN ('liability_credit_card', 'asset_cash')
                    ))
                """
            )
        else:
            return SQL('TRUE')

    def _query_bank_journal_initial_balance(self, options, journal_id):
        report = self.env.ref('account_reports.journal_report')
        query = report._get_report_query(options, 'to_beginning_of_period', domain=[('journal_id', '=', journal_id)])
        query = SQL(
            """
                SELECT
                    COALESCE(SUM(account_move_line.balance), 0) AS balance
                FROM %(table)s
                JOIN account_journal journal ON journal.id = "account_move_line".journal_id AND account_move_line.account_id = journal.default_account_id
                WHERE %(search_conditions)s
                GROUP BY journal.id
            """,
            table=query.from_clause,
            search_conditions=query.where_clause,
        )
        self._cr.execute(query)
        result = self._cr.dictfetchall()
        init_balance = result[0]['balance'] if len(result) >= 1 else 0
        return init_balance

    ##########################################################################
    # Tax Grids
    ##########################################################################

    def _section_has_tax(self, options, journal_id):
        report = self.env['account.report'].browse(options.get('report_id'))
        aml_has_tax_domain = [('tax_ids', '!=', False)]
        if journal_id:
            aml_has_tax_domain.append(('journal_id', '=', journal_id))
        aml_has_tax_domain += report._get_options_domain(options, 'strict_range')
        return bool(self.env['account.move.line'].search_count(aml_has_tax_domain, limit=1))

    def _get_tax_summary_section(self, options, journal_vals=None):
        """
        Get the journal tax summary if it is passed as parameter.
        In case no journal is passed, it will return the global tax summary data
        """
        tax_data = {
            'date_from': options.get('date', {}).get('date_from'),
            'date_to': options.get('date', {}).get('date_to'),
        }

        if journal_vals:
            tax_data['journal_id'] = journal_vals['id']
            tax_data['journal_type'] = journal_vals['type']

        tax_report_lines = self._get_generic_tax_summary_for_sections(options, tax_data)
        tax_non_deductible_column = any(line.get('tax_non_deductible_no_format') for country_vals_list in tax_report_lines.values() for line in country_vals_list)
        tax_deductible_column = any(line.get('tax_deductible_no_format') for country_vals_list in tax_report_lines.values() for line in country_vals_list)
        tax_due_column = any(line.get('tax_due_no_format') for country_vals_list in tax_report_lines.values() for line in country_vals_list)
        extra_columns = int(tax_non_deductible_column) + int(tax_deductible_column) + int(tax_due_column)

        tax_grid_summary_lines = self._get_tax_grids_summary(options, tax_data)

        return {
            'tax_report_lines': tax_report_lines,
            'tax_non_deductible_column': tax_non_deductible_column,
            'tax_deductible_column': tax_deductible_column,
            'tax_due_column': tax_due_column,
            'extra_columns': extra_columns,
            'tax_grid_summary_lines': tax_grid_summary_lines,
        }

    def _get_generic_tax_report_options(self, options, data):
        """
        Return an option dictionnary set to fetch the reports with the parameters needed for this journal.
        The important bits are the journals, date, and fetch the generic tax reports that contains all taxes.
        We also provide the information about wether to take all entries or only posted ones.
        """
        generic_tax_report = self.env.ref('account.generic_tax_report')
        previous_option = options.copy()
        # Force the dates to the selected ones. Allows to get it correctly when grouped by months
        previous_option.update({
            'selected_variant_id': generic_tax_report.id,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
        })
        tax_report_options = generic_tax_report.get_options(previous_option)
        journal_report = self.env['account.report'].browse(options['report_id'])
        tax_report_options['forced_domain'] = tax_report_options.get('forced_domain', []) + journal_report._get_options_domain(options, 'strict_range')

        # Even though it doesn't have a journal selector, we can force a journal in the options to only get the lines for a specific journal.
        if data.get('journal_id') or data.get('journal_type'):
            tax_report_options['journals'] = [{
                'id': data.get('journal_id'),
                'model': 'account.journal',
                'type': data.get('journal_type'),
                'selected': True,
            }]

        return tax_report_options

    def _get_tax_grids_summary(self, options, data):
        """
        Fetches the details of all grids that have been used in the provided journal.
        The result is grouped by the country in which the tag exists in case of multivat environment.
        Returns a dictionary with the following structure:
        {
            Country : {
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                ...
            },
            Country : [
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                ...
            ],
            ...
        }
        """
        report = self.env.ref('account_reports.journal_report')
        # Use the same option as we use to get the tax details, but this time to generate the query used to fetch the
        # grid information
        tax_report_options = self._get_generic_tax_report_options(options, data)
        query = report._get_report_query(tax_report_options, 'strict_range')
        country_name = self.env['res.country']._field_to_sql('country', 'name')
        tag_name = self.env['account.account.tag']._field_to_sql('tag', 'name')
        query = SQL("""
            WITH tag_info (country_name, tag_id, tag_name, tag_sign, balance) AS (
                SELECT
                    %(country_name)s AS country_name,
                    tag.id,
                    %(tag_name)s AS name,
                    CASE WHEN tag.tax_negate IS TRUE THEN '-' ELSE '+' END,
                    SUM(COALESCE("account_move_line".balance, 0)
                        * CASE WHEN "account_move_line".tax_tag_invert THEN -1 ELSE 1 END
                        ) AS balance
                FROM account_account_tag tag
                JOIN account_account_tag_account_move_line_rel rel ON tag.id = rel.account_account_tag_id
                JOIN res_country country ON country.id = tag.country_id
                , %(table_references)s
                WHERE %(search_condition)s
                  AND applicability = 'taxes'
                  AND "account_move_line".id = rel.account_move_line_id
                GROUP BY country_name, tag.id
            )
            SELECT
                country_name,
                tag_id,
                REGEXP_REPLACE(tag_name, '^[+-]', '') AS name, -- Remove the sign from the grid name
                balance,
                tag_sign AS sign
            FROM tag_info
            ORDER BY country_name, name
        """, country_name=country_name, tag_name=tag_name, table_references=query.from_clause, search_condition=query.where_clause)
        self._cr.execute(query)
        query_res = self.env.cr.fetchall()

        res = {}
        opposite = {'+': '-', '-': '+'}
        for country_name, tag_id, name, balance, sign in query_res:
            res.setdefault(country_name, {}).setdefault(name, {})
            res[country_name][name].setdefault('tag_ids', []).append(tag_id)
            res[country_name][name][sign] = report._format_value(options, balance, 'monetary')

            # We need them formatted, to ensure they are displayed correctly in the report. (E.g. 0.0, not 0)
            if not opposite[sign] in res[country_name][name]:
                res[country_name][name][opposite[sign]] = report._format_value(options, 0, 'monetary')

            res[country_name][name][sign + '_no_format'] = balance
            res[country_name][name]['impact'] = report._format_value(options, res[country_name][name].get('+_no_format', 0) - res[country_name][name].get('-_no_format', 0), 'monetary')

        return res

    def _get_generic_tax_summary_for_sections(self, options, data):
        """
        Overridden to make use of the generic tax report computation
        Works by forcing specific options into the tax report to only get the lines we need.
        The result is grouped by the country in which the tag exists in case of multivat environment.
        Returns a dictionary with the following structure:
        {
            Country : [
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                ...
            ],
            Country : [
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                {name, base_amount, tax_amount, tax_non_deductible{_no_format}, tax_deductible{_no_format}, tax_due{_no_format}},
                ...
            ],
            ...
        }
        """
        report = self.env['account.report'].browse(options['report_id'])
        tax_report_options = self._get_generic_tax_report_options(options, data)
        tax_report_options['account_journal_report_tax_deductibility_columns'] = True
        tax_report = self.env.ref('account.generic_tax_report')
        tax_report_lines = tax_report._get_lines(tax_report_options)

        tax_values = {}
        for tax_report_line in tax_report_lines:
            model, line_id = report._parse_line_id(tax_report_line.get('id'))[-1][1:]
            if model == 'account.tax':
                tax_values[line_id] = {
                    'base_amount': tax_report_line['columns'][0]['no_format'],
                    'tax_amount': tax_report_line['columns'][1]['no_format'],
                    'tax_non_deductible': tax_report_line['columns'][2]['no_format'],
                    'tax_deductible': tax_report_line['columns'][3]['no_format'],
                    'tax_due': tax_report_line['columns'][4]['no_format'],
                }

        # Make the final data dict that will be used by the template, using the taxes information.
        taxes = self.env['account.tax'].browse(tax_values.keys())
        res = {}
        for tax in taxes:
            res.setdefault(tax.country_id.name, []).append({
                'base_amount': report._format_value(options, tax_values[tax.id]['base_amount'], 'monetary'),
                'tax_amount': report._format_value(options, tax_values[tax.id]['tax_amount'], 'monetary'),
                'tax_non_deductible': report._format_value(options, tax_values[tax.id]['tax_non_deductible'], 'monetary'),
                'tax_non_deductible_no_format': tax_values[tax.id]['tax_non_deductible'],
                'tax_deductible': report._format_value(options, tax_values[tax.id]['tax_deductible'], 'monetary'),
                'tax_deductible_no_format': tax_values[tax.id]['tax_deductible'],
                'tax_due': report._format_value(options, tax_values[tax.id]['tax_due'], 'monetary'),
                'tax_due_no_format': tax_values[tax.id]['tax_due'],
                'name': tax.name,
                'line_id': report._get_generic_line_id('account.tax', tax.id)
            })

        # Return the result, ordered by country name
        return dict(sorted(res.items()))

    ##########################################################################
    # Actions
    ##########################################################################

    def journal_report_tax_tag_template_open_aml(self, options, params=None):
        """ returns an action to open a list view of the account.move.line having the selected tax tag """
        tag_ids = params.get('tag_ids')
        domain = (
            self.env['account.report'].browse(options['report_id'])._get_options_domain(options, 'strict_range')
            + [('tax_tag_ids', 'in', [tag_ids])]
            + self.env['account.move.line']._get_tax_exigible_domain()
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items for Tax Audit'),
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tax_audit_tree').id, 'list']],
            'domain': domain,
            'context': self.env.context,
        }

    def journal_report_action_dropdown_audit_default_tax_report(self, options, params):
        return self.env['account.generic.tax.report.handler'].caret_option_audit_tax(options, params)

    def journal_report_action_open_tax_journal_items(self, options, params):
        """
        Open the journal items related to the tax on this line.
        Take into account the given/options date and group by taxes then account.
        :param options: the report options.
        :param params: a dict containing the line params. (Dates, name, journal_id, tax_type)
        :return: act_window on journal items grouped by tax or tags and accounts.
        """
        ctx = {
            'search_default_posted': 0 if options.get('all_entries') else 1,
            'search_default_date_between': 1,
            'date_from': params and params.get('date_from') or options.get('date', {}).get('date_from'),
            'date_to': params and params.get('date_to') or options.get('date', {}).get('date_to'),
            'search_default_journal_id': params.get('journal_id'),
            'expand': 1,
        }
        if params and params.get('tax_type') == 'tag':
            ctx.update({
                'search_default_group_by_tax_tags': 1,
                'search_default_group_by_account': 2,
            })
        elif params and params.get('tax_type') == 'tax':
            ctx.update({
                'search_default_group_by_taxes': 1,
                'search_default_group_by_account': 2,
            })

        if params and 'journal_id' in params:
            ctx.update({
                'search_default_journal_id': [params['journal_id']],
            })

        if options and options.get('journals') and not ctx.get('search_default_journal_id'):
            selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected') and journal['model'] == 'account.journal']
            if len(selected_journals) == 1:
                ctx['search_default_journal_id'] = selected_journals

        return {
            'name': params.get('name'),
            'view_mode': 'list,pivot,graph,kanban',
            'res_model': 'account.move.line',
            'views': [(self.env.ref('account.view_move_line_tree').id, 'list')],
            'type': 'ir.actions.act_window',
            'domain': [('display_type', 'not in', ('line_section', 'line_note'))],
            'context': ctx,
        }

    def journal_report_action_open_account_move_lines_by_account(self, options, params):
        """
        Open a list view of the journal account move lines
        corresponding to the date filter and the current account line clicked
        :param options: The current options of the report
        :param params: The params given from the report UI (journal_id, account_id, date)
        :return: act_window on journal items filtered on the current journal and the current account within a date.
        """
        report = self.env['account.report'].browse(options['report_id'])
        journal = self.env['account.journal'].browse(params['journal_id'])
        account = self.env['account.account'].browse(params['account_id'])

        domain = [
            ('journal_id.id', '=', journal.id),
            ('account_id.id', '=', account.id),
        ]
        domain += report._get_options_domain(options, 'strict_range')

        return {
            'type': 'ir.actions.act_window',
            'name': _("%(journal)s - %(account)s", journal=journal.name, account=account.name),
            'res_model': 'account.move.line',
            'views': [[False, 'list']],
            'domain': domain
        }

    def journal_report_open_aml_by_move(self, options, params):
        report = self.env['account.report'].browse(options['report_id'])
        journal = self.env['account.journal'].browse(params['journal_id'])

        context_update = {
            'search_default_group_by_account': 0,
            'show_more_partner_info': 1,
        }

        if journal.type in ('bank', 'credit'):
            params['view_ref'] = 'account_reports.view_journal_report_audit_bank_move_line_tree'
            context_update['search_default_exclude_bank_lines'] = 1
        else:
            params['view_ref'] = 'account_reports.view_journal_report_audit_move_line_tree'
            context_update.update({
                'search_default_group_by_partner': 1,
                'search_default_group_by_move': 2,
            })
            if journal.type in ('sale', 'purchase'):
                context_update['search_default_invoices_lines'] = 1

        action = report.open_journal_items(options=options, params=params)
        action.get('context', {}).update(context_update)
        return action
