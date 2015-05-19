#!/usr/bin/env python


import locale
import os
import json
import csv
import markdown



locale.setlocale(locale.LC_ALL, 'en_US.utf-8')

basedir = ''
genPath = 'gen'
genConditionsPath = 'gen/conditions/'
tempPath = 'temp'
input_dxtx_path = 'external-input/'
output_dxtx_path = 'temp/html-dxtx/'
tempTablesPath = 'temp/tables/'
regimenStore = {}             # store metadata for tables
conditionStore = []           # store condition for Condition Quick Pick feature
REPLACE_IMAGE_WITH_HTML_TAG = "replace-image-with-html"
REPLACE_IMAGE_WITH_CONDITION_TAG = "replace-image-with-condition"


class Breadcrumb:
    def __init__(self, text, link):
        self.text = text
        self.link = link


class RegimenTableRow:
    def __init__(self, regimen_type, text):
        self.regimen_type = regimen_type
        self.text = text

SUB_HEADER_TYPE = 1
REGIMEN_TYPE = 2
SEPARATOR_TYPE = 3
FOOTER_TYPE = 4
GROUPED_SEPARATOR_TYPE = 5


# Class representing table data
class RegimenTableData:
    def __init__(self):
        self.rows = []
        self.header = ""
        self.htmlFile = ""
        self.tableId = ""
        self.subHeaderType = 1
        self.regimenType = 2

    def add_table(self, table):
        self.tableId = table

    def add_header(self, header):
        self.header = header

    def add_sub_header(self, text):
        row = RegimenTableRow(SUB_HEADER_TYPE, text)
        self.rows.append(row)

    def add_regimen(self, text):
        row = RegimenTableRow(REGIMEN_TYPE, text)
        self.rows.append(row)

    def add_separator(self, text):
        row = RegimenTableRow(SEPARATOR_TYPE, text)
        self.rows.append(row)

    def add_grouped_separator(self, text):
        row = RegimenTableRow(GROUPED_SEPARATOR_TYPE, text)
        self.rows.append(row)

    def add_footer(self, text):
        row = RegimenTableRow(FOOTER_TYPE, text)
        self.rows.append(row)

    def write_to_file(self, tf):
        tf.write('''
        <div id="table">
            <div id="regimen_header">''')
        tf.write(self.header)
        tf.write('''
            </div>
            <hr/>
            <span class="regimen_text">''')

        for row in self.rows:
            assert isinstance(row, RegimenTableRow)
            if row.regimen_type == SUB_HEADER_TYPE:
                tf.write('''</br>
                <div id="regimen_subheader">''')
                tf.write(row.text)
                tf.write('''</br></div>''')

            elif row.regimen_type == REGIMEN_TYPE:
                tf.write(row.text)

            elif row.regimen_type == SEPARATOR_TYPE:
                tf.write('''
            <div id="or">''')
                tf.write(row.text)
                tf.write('''</div>''')

            elif row.regimen_type == GROUPED_SEPARATOR_TYPE:
                tf.write('''
            <div id="or">
                <hr/>''')
                tf.write(row.text)
                tf.write('''
                <hr/>
            </div>''')

        tf.write('''
            </span>
''')
        for row in self.rows:
            assert isinstance(row, RegimenTableRow)

            if row.regimen_type == FOOTER_TYPE:
                tf.write('''
            <hr/>
                <p class="regimen_footer_text">''')
                tf.write(row.text)
                tf.write('''</p>''')

        tf.write('''
        </div>
        <br />
''')

    def write_table_temp_html_file(self):
        # write out contents of original file
        # may delete this later as unnecessary
        self.htmlFile = "temp/tables/" + self.tableId + ".html"
        print "HTML file =", self.htmlFile

        # done processing chapter file, write it out as HTML
        with open(self.htmlFile, "w") as tf:
            try:
                self.write_to_file(tf)
            finally:
                tf.close()

    def read_lines_from_table_html_file(self):
        # read contents of temp file
        with open(self.htmlFile, "r") as tf:
            lines = tf.readlines()
        return lines


class Condition:
    def __init__(self, condition_id, parent, text):
        self.condition_id = condition_id
        if parent is None:
            self.parent = parent
        else:
            self.parent = parent.condition_id
        self.text = text
        self.breadcrumbs = []
        self.children = []
        self.hasChildren = False
        self.regimens = []
        self.pageId = 'c' + str(self.condition_id)
        self.regimensPageId = self.pageId + '-r'
        self.regimensPage = self.regimensPageId + '.html'
        self.hasRegimens = False
        self.dxtx = []
        self.dxtxPageId = self.pageId + '-t'
        self.dxtxPage = self.dxtxPageId + '.html'
        self.hasDxTx = False
        self.childrenListViewPageId = self.pageId + '-clv'
        self.childrenListViewPage = self.childrenListViewPageId + '.html'

        if parent is None or condition_id == 0:
            self.childBreadcrumbs = ''
        else:
            if parent.childBreadcrumbs == '':
                self.childBreadcrumbs = self.text
            else:
                self.childBreadcrumbs = parent.childBreadcrumbs + ' / ' + self.text

    def add_child(self, child_condition):
        self.children.append(child_condition)
        self.hasChildren = True

    def add_breadcrumb(self, breadcrumb):
        self.breadcrumbs.append(breadcrumb)

    def create_my_breadcrumb(self):
        return Breadcrumb(self.text, self.childrenListViewPage)

    def add_regimen(self, regimen):
        if len(regimen) >= 5:
            self.regimens.append(regimen)
            self.hasRegimens = True
        elif regimen == '' and len(self.regimens) == 0:
            self.hasRegimens = False

    def add_dxtx(self, dxtx):
        if dxtx > 1:
            self.dxtx.append(dxtx)
            self.hasDxTx = True
        elif dxtx == '' and len(self.dxtx) == 0:
            self.hasDxTx = False

    def write_html_files(self):
        if self.hasChildren:
            self.write_html_children_list_view()
        self.write_html_regimens()
        self.write_html_dxtx()

    def write_html_children_list_view(self):
        # write current heading, and content between current and next heading
        # to heading content file as HTML using heading ID as name
        with open(genConditionsPath + self.childrenListViewPage, "w") as lvf:
            try:
                self.write_condition_common_head(lvf)
                self.write_html_page_header(lvf)
                self.write_children_listview_body(lvf)
            finally:
                lvf.close()

    def write_html_regimens(self):
        if self.hasRegimens:
            # write current heading, and content between current and next heading
            # to heading content file as HTML using heading ID as name

            with open(genConditionsPath + self.regimensPage, "w") as reg_f:
                try:
                    self.write_condition_common_head(reg_f)
                    self.write_html_page_header(reg_f)
                    self.write_html_regimens_content(reg_f)
                    self.write_html_regimens_footer(reg_f)
                finally:
                    reg_f.close()
        else:
            self.regimensPage = ''

    def write_html_dxtx(self):
        if self.hasDxTx:
            # write current heading, and content between current and next heading
            # to heading content file as HTML using heading ID as name
            with open(genConditionsPath + self.dxtxPage, "w") as dxtx_f:
                try:
                    self.write_condition_common_head(dxtx_f)
                    self.write_html_page_header(dxtx_f)
                    self.write_html_dxtx_content(dxtx_f)
                    self.write_html_dxtx_footer(dxtx_f)

                finally:
                    dxtx_f.close()
        else:
            self.dxtxPage = ''

    def write_condition_common_head(self, html_file):
        html_file.write('''<!DOCTYPE html>
<html lang="en">
    <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>''')

        html_file.write(str(self.condition_id))
        html_file.write('''</title>

        <link href="bootstrap.min.css" rel="stylesheet">
        <link href="custom_arrow.css" rel="stylesheet" type="text/css"/>
        <link href="treatments.css" rel="stylesheet" type="text/css"/>
        <link href="recreated_tables.css" rel="stylesheet" type="text/css"/>
           <style>
        .sep {
            border-bottom:1px solid lightgray;
        }
        .sep td {
            padding-bottom:5px;
            padding-top:5px;
        }
        br {
            display: block;
            margin-top: 5px 0;
        }
    </style>
    </head>''')

    @staticmethod
    def write_html_page_header(html_file):
        html_file.write('''
    <body>''')

    def write_html_breadcrumbs(self, html_file):
    # do not write breadcrumbs for root condition
        if self.condition_id != 0:

            html_file.write('''
            <br />
            <div class="container">
                <ol class="breadcrumb small">
                ''')
            html_file.write('''
                        ''')
            if len(self.breadcrumbs):
                for index, breadcrumb in enumerate(self.breadcrumbs):
                    assert isinstance(breadcrumb, Breadcrumb)
                    html_file.write('''<li class="active">''')
                    html_file.write(breadcrumb.text)
                    html_file.write('''</li>''')

            html_file.write('''<li class="active">''')
            html_file.write(self.text)
            html_file.write('''</li>''')
            html_file.write('''
                </ol>
              </div><!-- end of breadcrumbs -->
            ''')

    def write_html_regimens_content(self, html_file):

        self.write_html_breadcrumbs(html_file)

        html_file.write('''
        <div class="container">''')

        # write out all the regimen tables
        if len(self.regimens) != 0:
            for regimenId in self.regimens:
                regimen = regimenStore[regimenId]
                assert isinstance(regimen, RegimenTableData)
                regimen.write_to_file(html_file)

        html_file.write('''
        </div>''')

    def write_html_dxtx_content(self, html_file):

        self.write_html_breadcrumbs(html_file)

        html_file.write('''
        <div class="container">''')

        # write out all dxtx sections
        if len(self.dxtx) != 0:
            for dxtx in self.dxtx:
                 with open(output_dxtx_path + dxtx + ".html", "r") as section_f:
                    try:
                            ## Read the first line
                        line = section_f.readline()

                        ## search for cond-table-insert tags and throw them away
                        while line:

                            if REPLACE_IMAGE_WITH_CONDITION_TAG in line:
                                table_id = section_f.readline().strip()
                                regimen_table = regimenStore[table_id]
                                regimen_data = regimen_table.read_lines_from_table_html_file()
                                html_file.writelines(regimen_data)
                                #read closing cond-table-insert tag
                                line = section_f.readline()
                            elif REPLACE_IMAGE_WITH_HTML_TAG in line:
                                htmlSnippetFileName = section_f.readline().strip()
                                with open("input/image-replace/" + htmlSnippetFileName) as htmlSnippetFile:
                                    try:
                                        htmlSnippetData = htmlSnippetFile.readlines()
                                        html_file.writelines(htmlSnippetData)
                                    except IOError:
                                        print "Can not open HTML snippet %s for image replacement." % htmlSnippetFileName
                                    finally:
                                        htmlSnippetFile.close()
                            else:
                                html_file.write(line)
                            line = section_f.readline()

                    finally:
                        section_f.close()

        html_file.write('''
        </div>''')

    @staticmethod
    def write_html_regimens_footer(html_file):
        html_file.write('''
            </div>
        </div>
    </body>
</html>
        ''')

    @staticmethod
    def write_html_dxtx_footer(html_file):
        html_file.write('''
            </div>
        </div>
    </body>
</html>
        ''')

    def write_children_listview_body(self, html_file):

        html_file.write('''
            <div data-role="content" data-theme="a" >''')
        self.write_html_breadcrumbs(html_file)
        html_file.write('''
                <ul data-count-theme="b" data-role="listview" data-inset="true" data-divider-theme="a">''')
        for child in self.children:
            assert isinstance(child, Condition)
            html_file.write('''
                    <li><a href="''')
            if child.hasChildren:
                html_file.write(child.childrenListViewPage)
            elif child.hasRegimens:
                html_file.write(child.regimensPage)
            elif child.hasDxTx:
                html_file.write(child.dxtxPage)
            html_file.write('''"><span style="white-space:normal;">''')
            html_file.write(child.text)
            html_file.write('''</span></a></li>''')

        html_file.write('''
                </ul>
            </div>
        ''')
#        write_menu_panel(html_file)
        html_file.write('''
        </div>
    </body>
</html>
        ''')


# writes out regimen data found in table-data.txt into individual html files named
# in a "doc-page-column-table.html" format to /temp/tables directory
def import_regimen_table_data(table_file):

    table_found = False
    table_cnt = 0

    # create a new JSON file that contains all the condition metadata
    with open(table_file, "r") as csv_f:
        csv_reader = csv.reader(csv_f)
        for row in csv_reader:
            if row:
                blank_row_found = False
                if row[0][0] == '#':
                    print "Comment = %s" % (row[0])
                    continue
                if len(row) == 2:
                    key = row[0]
                    value = row[1]
                    #print "Row = %s, %s" % (row[0], row[1])
                    if key == 'table':
                        # print "Table = %s" % row[1]
                        table_data = RegimenTableData()
                        table_data.add_table(value)
                        table_found = True
                    elif key == 'header':
                        table_data.add_header(value)
                    elif key == 'subheader':
                        table_data.add_sub_header(value)
                    elif key == 'regimen':
                        table_data.add_regimen(value)
                    elif key == 'separator':
                        table_data.add_separator(value)
                    elif key == "grouped-separator":
                        table_data.add_grouped_separator(value)
                    elif key == 'footer':
                        table_data.add_footer(value)
                        print("Footer value =  " + value)

                    print "Key = %s, value = %s" % (key, value)

                elif len(row) == 1:
                    print "Row = %s" % (row[0])
                    continue

            else:
                blank_row_found = True

            if blank_row_found and table_found:
                table_cnt += 1
                table_found = False

                # write out HTML version of table data to file
                table_data.write_table_temp_html_file()
                # store table data for later processing
                regimenStore[table_data.tableId] = table_data
    csv_f.close()
    print "Table count = %d" % table_cnt


def json_default(o):
    return o.__dict__


def create_condition_map(fl):
    global genPath

    # condition_map = {}
    # content_id = 0

    with open(fl, "w") as tf:
        try:
            json.dump(conditionStore[0], tf, default=json_default, indent=4)
        finally:
            tf.close()


def import_condition_data(table_file):

    condition_found = False
    condition1 = None
    condition2 = None
    breadcrumb1 = None
    breadcrumb2 = None
    condition_id = 0

    # create root condition
    root_condition = Condition(condition_id, None, 'Condition Quick Pick')
    root_breadcrumb = Breadcrumb('Condition Quick Pick', root_condition.childrenListViewPage)
    conditionStore.append(root_condition)
    condition_id = 1

    # open file, read line by line, until blank line found
    with open(table_file, "r") as csv_f:
        csv_reader = csv.reader(csv_f)
        for row in csv_reader:
            if row:
                blank_row_found = False
                if row[0][0] == '#':
                    print "Comment = %s" % (row[0])
                    continue
                if len(row) >= 2:
                    key = row[0]
                    value = row[1]
                    #print "Row = %s, %s" % (row[0], row[1])
                    if key == 'cond1':
                        # print "List 1 = %s" % row[1]
                        condition = Condition(condition_id, root_condition, value)
                        condition1 = condition
                        condition_id += 1
                        condition_found = True
                        breadcrumb1 = condition.create_my_breadcrumb()
                        #condition.add_breadcrumb(root_breadcrumb)
                        root_condition.add_child(condition1)
                        conditionStore.append(condition)
                    elif key == 'cond2':
                        condition = Condition(condition_id, condition1, value)
                        condition2 = condition
                        condition_id += 1
                        condition1.add_child(condition2)
                        breadcrumb2 = condition.create_my_breadcrumb()
                        #condition.add_breadcrumb(root_breadcrumb)
                        condition.add_breadcrumb(breadcrumb1)
                        conditionStore.append(condition)
                    elif key == 'cond3':
                        condition = Condition(condition_id, condition2, value)
                        condition_id += 1
                        condition2.add_child(condition)
                        condition.create_my_breadcrumb()
                        #condition.add_breadcrumb(root_breadcrumb)
                        condition.add_breadcrumb(breadcrumb1)
                        condition.add_breadcrumb(breadcrumb2)
                        conditionStore.append(condition)
                    elif key == 'regimens':
                        for i in range(1, len(row)):
                            condition.add_regimen(row[i])
                    elif key == 'dx-tx':
                        for i in range(1, len(row)):
                            condition.add_dxtx(row[i])
                    print "Key = %s, value = %s" % (key, value)
                elif len(row) == 1:
                    print "Row = %s" % (row[0])
                    continue

            else:
                blank_row_found = True

            if blank_row_found and condition_found:
                condition_found = False
                condition1 = condition2 = None
                breadcrumb1 = breadcrumb2 = None
    csv_f.close()

    for condition in conditionStore:
        condition.write_html_files()


def init_dirs():
    global genConditionsPath, input_dxtx_path, output_dxtx_path, tempTablesPath
    """Builds directory structure"""
    if not os.path.exists(genConditionsPath):
        os.makedirs(genConditionsPath)
        print("Creating gen conditions path " + genConditionsPath + "...")
    else:
        print("Gen conditions path " + genConditionsPath + " exists...")

    if not os.path.exists(input_dxtx_path):
        print("Error: DxTx content path " + input_dxtx_path + "does not exist!!!")

    if not os.path.exists(output_dxtx_path):
        print("Error: DxTx output path " + output_dxtx_path + "does not exist!!!")

    if not os.path.exists(tempTablesPath):
        os.makedirs(tempTablesPath)
        print("Creating temp tables path " + tempTablesPath + "...")
    else:
        print("Temp tables path " + tempTablesPath + " exists...")

    print("Creation of directories complete.")


def process_markdown_files():

    for markdown_file in os.listdir(input_dxtx_path):
        print("Markdown file = " + markdown_file)
        if markdown_file.endswith(".txt"):
            html_file = os.path.splitext(markdown_file)[0] + '.html'
            html_file_path = os.path.join(output_dxtx_path, html_file)
            markdown_file_path = os.path.join(input_dxtx_path, markdown_file)
            print("Parsing markdown file " + markdown_file_path + " and saving as as html file " + html_file_path)

            # use footnote extensions
            markdown.markdownFromFile(input=markdown_file_path, output=html_file_path,  extensions=['markdown.extensions.footnotes', 'markdown.extensions.tables'])


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument('-t', '--tables', help='CSV table data file')
    parser.add_argument('-m', '--metadata', help='Metadata file')

    args = parser.parse_args()

    init_dirs()
    try:
        # process DxTx files that are written using Markdown markup syntax
        process_markdown_files()
        import_regimen_table_data("external-input/table-data.txt")
        import_condition_data("external-input/cqp-metadata.txt")
        create_condition_map("gen/condition-content-map.txt")
    except KeyboardInterrupt:
        pass

    # if args.table:
    #     try:
    #         import_table_data("input/table-data.txt")
    #         import_condition_data("metadata/cqp-metadata.txt")
    #     except KeyboardInterrupt:
    #         pass
