#!/usr/bin/env python


import locale, os
import json
import csv

import BeautifulSoup

locale.setlocale(locale.LC_ALL, 'en_US.utf-8')

basedir = ''
genPath = 'gen'
tempPath = 'temp'
regimenStore = {}             # store metadata for tables
conditionStore = []           # store condition for Condition Quick Pick feature



class Breadcrumb():
    def __init__(self, text, link):
        self.text = text
        self.link = link



class RegimenTableRow():
    def __init__(self, type, text):
        self.type = type
        self.text = text

SUB_HEADER_TYPE = 1
REGIMEN_TYPE = 2
SEPARATOR_TYPE = 3
FOOTER_TYPE = 4
GROUPED_SEPARATOR_TYPE = 5

# Class representing table data
class RegimenTableData():
    def __init__(self):
        self.rows = []
        self.condition = ""
        self.patient = ""
        self.doc = ""
        self.page = ""
        self.column = ""
        self.table = ""
        self.header = ""
        self.htmlFile = ""
        self.tableId = ""
        self.subHeaderType = 1
        self.regimenType = 2

    def addCondition(self, condition):
        self.condition = condition
    def addPatient(self,patient):
        self.patient = patient
    def addHeader(self, header):
        self.header = header
    def addSubHeader(self, text):
        row = RegimenTableRow(SUB_HEADER_TYPE, text)
        self.rows.append(row)
    def addRegimen(self, text):
        row = RegimenTableRow(REGIMEN_TYPE, text)
        self.rows.append(row)
    def addSeparator(self, text):
        row = RegimenTableRow(SEPARATOR_TYPE, text)
        self.rows.append(row)
    def addGroupedSeparator(self, text):
        row = RegimenTableRow(GROUPED_SEPARATOR_TYPE, text)
        self.rows.append(row)
    def addFooter(self, text):
        row = RegimenTableRow(FOOTER_TYPE, text)
        self.rows.append(row)
    def addDoc(self,doc):
        self.doc = doc
    def addPage(self, page):
        self.page = page
    def addColumn(self, column):
        self.column = column
    def addTable(self, table):
        self.table = table
        self.tableId = self.doc + '-' + self.page + '-' + self.column + '-' + self.table
    def writeToFile(self,tf):
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
            if row.type == SUB_HEADER_TYPE:
                tf.write('''</br>
                <div id="regimen_subheader">''')
                tf.write(row.text)
                tf.write('''</br></div>''')


            elif row.type == REGIMEN_TYPE:
                tf.write(row.text)

            elif row.type == SEPARATOR_TYPE:
                tf.write('''
            <div id="or">''')
                tf.write(row.text)
                tf.write('''</div>''')

            elif row.type == GROUPED_SEPARATOR_TYPE:
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

            if row.type == FOOTER_TYPE:
                tf.write('''
            <hr/>
                <p class="regimen_footer_text">''')
                tf.write(row.text)
                tf.write('''</p>''')

        tf.write('''
        </div>
''')

    def writeTableTempHtmlFile(self):
        # write out contents of original file
        # may delete this later as unnecessary
        self.htmlFile = "temp/tables/" + self.tableId + ".html"
        print "HTML file =", self.htmlFile

        # done processing chapter file, write it out as HTML
        with open(self.htmlFile, "w") as tf:
            try:
                self.writeToFile(tf)
            finally:
                tf.close()

    def readLinesFromTableHtmlFile(self):
        # read contents of temp file
        lines = []
        with open(self.htmlFile, "r") as tf:
            lines = tf.readlines()
        return lines





#region Common Head for HTML files

#endregion


class Condition():
    def __init__(self, id, parent, text):
        self.id = id
        if parent is None:
            self.parent = parent
        else:
            self.parent = parent.id
        self.text = text
        self.breadcrumbs = []
        self.children = []
        self.hasChildren = False
        self.regimens =[]
        self.pageId = 'c' + str(id)
        self.regimensPageId = self.pageId + '-r'
        self.regimensPage = self.regimensPageId + '.html'
        self.hasRegimens = False
        self.dxtx = []
        self.dxtxPageId = self.pageId + '-t'
        self.dxtxPage = self.dxtxPageId + '.html'
        self.hasDxTx = False
        self.childrenListViewPageId = self.pageId + '-clv'
        self.childrenListViewPage = self.childrenListViewPageId  + '.html'

    def addChild(self, childCondition):
        self.children.append(childCondition)
        self.hasChildren = True
    def addBreadcrumb(self, breadcrumb):
        self.breadcrumbs.append(breadcrumb)
    def createMyBreadcrumb(self):
        return Breadcrumb(self.text, self.childrenListViewPage)
    def addRegimen(self,regimen):
        if len(regimen) >= 5:
            self.regimens.append(regimen)
            self.hasRegimens = True
    def addDxTx(self, dxtx):
        self.dxtx.append(dxtx)
        self.hasDxTx = True

    def write_html_files(self):
        if self.hasChildren:
            self.write_html_children_list_view()
        if self.hasRegimens:
            self.write_html_regimens()
        if self.hasDxTx:
            self.write_html_dxtx()

    def write_html_children_list_view(self):
        # write current heading, and content between current and next heading
        # to heading content file as HTML using heading ID as name
        with open('gen/conditions/'+ self.childrenListViewPage, "w") as lvf:
            try:
                self.write_condition_common_head(lvf)
                self.write_html_page_header(lvf, self.childrenListViewPageId)
                self.write_children_listview_body(lvf)
            finally:
                lvf.close()
    def write_html_regimens(self):
        # write current heading, and content between current and next heading
        # to heading content file as HTML using heading ID as name
        with open('gen/conditions/' + self.regimensPage, "w") as regf:
            try:
                self.write_condition_common_head(regf)
                self.write_html_page_header(regf, self.regimensPageId)
                self.write_html_regimens_content(regf)
                self.write_html_regimens_footer(regf)
            finally:
                regf.close()

    def write_html_dxtx(self):
        # write current heading, and content between current and next heading
        # to heading content file as HTML using heading ID as name
        with open('gen/conditions/' + self.dxtxPage, "w") as dxtxf:
            try:
                self.write_condition_common_head(dxtxf)
                self.write_html_page_header(dxtxf, self.dxtxPageId)
                self.write_html_dxtx_content(dxtxf)
                self.write_html_dxtx_footer(dxtxf)

            finally:
                dxtxf.close()

    def write_condition_common_head(self,html_file):
        html_file.write('''<!DOCTYPE html>
<html>
    <head>
        <title>''')

        html_file.write(str(self.id))
        html_file.write('''</title>

    </head>''')

    def write_condition_dxtx_head(self,html_file):
        html_file.write('''<!DOCTYPE html>
<html>
    <head>
        <title>''')

        html_file.write(str(self.id))
        html_file.write('''</title>

    </head>''')

    def write_html_page_header(self, html_file, pageId):
        html_file.write('''
    <body>
        <div data-role="page" id="''')
        html_file.write(pageId)
        html_file.write('''" data-theme="a">
            <div data-id="quickpick-header" data-role="header" data-theme="b" data-position="fixed">''')


        html_file.write('''
                <h1>Condition Quick Pick</h1>
        ''')
        html_file.write('''    </div>''')

    def write_html_breadcrumbs(self, html_file):
    # do not write breadcrumbs for root condition
        if self.id != 0:
            html_file.write('''
                <div id=quickpick_breadcrumbs>
                ''')
            if len(self.breadcrumbs):
                for index, breadcrumb in enumerate(self.breadcrumbs):
                    assert isinstance(breadcrumb, Breadcrumb)

                    html_file.write('''
                        <a href="''')
                    html_file.write(breadcrumb.link)
                    html_file.write('''" >''')
                    html_file.write(breadcrumb.text)
                    html_file.write('''</a>''')

                    html_file.write('<span class="carrot"> > </span>')

            html_file.write(self.text)

            html_file.write('''
                </div>   <!-- end of quick pick breadcrumbs -->
                </br>''')


    def write_html_regimens_content(self,html_file):
        html_file.write('''
            <div data-role="content" data-theme="a" >''')

        self.write_html_breadcrumbs(html_file)

        # write out all the regimen tables
        if len(self.regimens) != 0:
            for regimenId in self.regimens:
                regimen = regimenStore[regimenId]
                assert isinstance(regimen, RegimenTableData)
                regimen.writeToFile(html_file)

    def write_html_dxtx_content(self,html_file):
        html_file.write('''
            <div data-role="content" data-theme="a" >''')

        self.write_html_breadcrumbs(html_file)

        # write out all dxtx sections
        if len(self.dxtx) != 0:
            for dxtx in self.dxtx:
                with open("temp/heading-content-raw/" + dxtx + ".html","r") as sectionf:
                    try:
                            ## Read the first line
                        line = sectionf.readline()

                        ## search for cond-table-insert tags and throw them away
                        while line:

                            # from epub2jqm
                            # if REPLACE_IMAGE_WITH_CONDITION_TAG in line:
                            #     line = sectionf.readline()   #read table ID
                            #     line = sectionf.readline()   #read closing cond-table-insert tag
                            # else:
                            #     html_file.write(line)

                            html_file.write(line)
                            line = sectionf.readline()

                    finally:
                        sectionf.close()

    def write_html_regimens_footer(self, html_file):

        html_file.write('''
            <div data-role="footer" data-id="regimens-footer" data-position="fixed" class="tab_treatment">
                <div data-role="navbar" class="tab_icons" data-iconpos="left">
                    <ul>
                        <li><a href="#" id="treat_active" data-theme="b" class="ui-btn-active ui-state-persist" data-icon="custom">Treatments</a></li>
                        <li><a href="''')
        if self.hasDxTx:
            html_file.write(self.dxtxPage + '"')
        else:
            html_file.write('#" class="ui-disabled"')
        html_file.write(''' id="info_inactive" data-theme="a" data-icon="custom">More Info</a></li>
                    </ul>
                </div>
            </div>
        </div>
        ''')
#       write_menu_panel(html_file)
        html_file.write('''
        </div>
    </body>
</html>
        ''')


    def write_html_dxtx_footer(self, html_file):

        html_file.write('''
            <div data-role="footer" data-id="regimens-footer" data-position="fixed" class="tab_treatment">
                <div data-role="navbar" class="tab_icons" data-iconpos="left">
                    <ul>
                        <li><a href="''')
        if self.hasRegimens:
            html_file.write(self.regimensPage  + '"')
        else:
            html_file.write('#" class="ui-disabled"')

        html_file.write(''' id="treat_inactive" data-theme="a" data-icon="custom">Treatments</a></li>
                        <li><a href="#" id="info_active" data-theme="b" class="ui-btn-active ui-state-persist" data-icon="custom">More Info</a></li>
                    </ul>
                </div>
            </div>

        </div>
        ''')
#        write_menu_panel(html_file)
        html_file.write('''
        </div>
    </body>
</html>
        ''')

    def write_children_listview_body(self,html_file):

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

    condition_found = False
    blank_row_found = False

    table_cnt = 0
    try:

        # create a new JSON file that contains all the condition metadata
        with open(table_file, "r") as csvf:
            csv_reader = csv.reader(csvf)
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
                        if key == 'condition':
                            # print "Condition = %s" % row[1]
                            tableData = RegimenTableData()
                            tableData.addCondition(value)
                            condition_found  = True
                        elif key == 'patient':
                            tableData.addPatient(value)
                        elif key == 'doc':
                            tableData.addDoc(value)
                        elif key == 'doc-page':
                            tableData.addPage(value)
                        elif key == 'doc-column':
                            tableData.addColumn(value)
                        elif key == 'table-in-column':
                            tableData.addTable(value)
                        elif key == 'header':
                            tableData.addHeader(value)
                        elif key == 'subheader':
                            tableData.addSubHeader(value)
                        elif key == 'regimen':
                            tableData.addRegimen(value)
                        elif key == 'separator':
                            tableData.addSeparator(value)
                        elif key == "grouped-separator":
                            tableData.addGroupedSeparator(value)
                        elif key == 'footer':
                            tableData.addFooter(value)
                        print "Key = %s, value = %s" % (key, value)

                    elif len(row) == 1:
                        print "Row = %s" % (row[0])
                        continue

                else:
                    blank_row_found = True

                if blank_row_found and condition_found:
                    table_cnt += 1
                    blank_row_found = False
                    condition_found = False

                    # write out HTML version of table data to file
                    tableData.writeTableTempHtmlFile()
                    # store table data for later processing
                    regimenStore[tableData.tableId] = tableData

    finally:
        print "Table count = %d" % table_cnt
        csvf.close()

def jdefault(o):
    return o.__dict__

def create_condition_map(fl):
    global genPath
    conditionMap = {}

    content_id = 0

    with open(fl, "w") as tf:
        try:
            json.dump(conditionStore[0], tf, default=jdefault, indent=4)
        finally:
            tf.close()


    # # create a new JSON file that contains all the headings metadata
    # with open(fl, "w") as f:
    #     try:
    #         # write conditions as an array
    #
    #         for condition in conditionStore:
    #             print "Condition %s has parent condition %s" % (condition.text, condition.parent)
    #             if condition.hasChildren:
    #                 conditionMap.append( {'id':condition.id, 'title':condition.text, 'parent':condition.parent, 'hasRegimens':condition.hasRegimens,
    #                                         'regimensPage':condition.regimensPage, 'dxtxPage':condition.dxtxPage, 'hasChildren':True })
    #             else:
    #                 conditionMap.append( {'id':condition.id, 'title':condition.text, 'parent':condition.parent, 'hasRegimens':condition.hasRegimens,
    #                                         'regimensPage':condition.regimensPage, 'dxtxPage':condition.dxtxPage})
    #
                # content_id += 1
                #
                # # do some post processing
                # for parenConditionId in conditionMap.keys():
                #     childConditions = []
                #     for childConditionId in conditionMap.keys():
                #         if conditionMap[childConditionId]['parent'] == parenConditionId:
                #             childConditions.append(childConditionId)
                #     if len(childConditions) != 0:
                #         conditionMap[parenConditionId]['hasChildren'] = True
                #         dict = conditionMap[parenConditionId]
                #         dict['children'] = childConditions
                #         conditionMap[parenConditionId] = dict
                #         # print "Parent ID of", parentHeadingId, "has children ", childHeadings
                #     else:
                #         conditionMap[parenConditionId]['hasChildren'] = False
                #         # print "Parent ID of %d has no children" % (parentHeadingId)

        # finally:
        #     json.dump(conditionMap, f, indent=4)
        # f.close()



####

        # self.id = id
        # self.parent = parent
        # self.text = text
        # self.breadcrumbs = []
        # self.children = []
        # self.hasChildren = False
        # self.regimens =[]
        # self.pageId = 'c' + str(id)
        # self.regimensPageId = self.pageId + '-r'
        # self.regimensPage = self.regimensPageId + '.html'
        # self.hasRegimens = False
        # self.dxtx = []
        # self.dxtxPageId = self.pageId + '-t'
        # self.dxtxPage = self.dxtxPageId + '.html'
        # self.hasDxTx = False
        # self.childrenListViewPageId = self.pageId + '-clv'
        # self.childrenListViewPage = self.childrenListViewPageId  + '.html'
        #


####



def import_condition_data(table_file):

    conditionFound = False
    blankRowFound = False
    condition1 = None
    condition2 = None
    condition3 = None
    breadcrumb1 = None
    breadcrumb2 = None
    breadcrumb3 = None
    condId = 0

    # create root condition
    rootCond = Condition(condId, None, 'Condition Quick Pick')
    rootBreadcrumb = Breadcrumb('Condition Quick Pick', rootCond.childrenListViewPage)
    conditionStore.append(rootCond)
    condId = 1

    try:

        # open file, read line by line, until blank line found
        with open(table_file, "r") as csvf:
            csvReader = csv.reader(csvf)
            for row  in csvReader:
                if row:
                    blankRowFound = False
                    if row[0][0] == '#':
                        print "Comment = %s" % (row[0])
                        continue
                    if len(row) >= 2:
                        key = row[0]
                        value = row[1]
                        #print "Row = %s, %s" % (row[0], row[1])
                        if key == 'cond1':
                            # print "List 1 = %s" % row[1]
                            condition = Condition(condId, rootCond, value)
                            condition1 = condition
                            condId += 1
                            conditionFound = True
                            breadcrumb1 = condition.createMyBreadcrumb()
                            condition.addBreadcrumb(rootBreadcrumb)
                            rootCond.addChild(condition1)
                            conditionStore.append(condition)
                        elif key == 'cond2':
                            condition = Condition(condId, condition1, value)
                            condition2 = condition
                            condId += 1
                            condition1.addChild(condition2)
                            breadcrumb2 = condition.createMyBreadcrumb()
                            condition.addBreadcrumb(rootBreadcrumb)
                            condition.addBreadcrumb(breadcrumb1)
                            conditionStore.append(condition)
                        elif key == 'cond3':
                            condition = Condition(condId, condition2, value)
                            condition3 = condition
                            condId += 1
                            condition2.addChild(condition3)
                            breadcrumb3 = condition.createMyBreadcrumb()
                            condition.addBreadcrumb(rootBreadcrumb)
                            condition.addBreadcrumb(breadcrumb1)
                            condition.addBreadcrumb(breadcrumb2)
                            conditionStore.append(condition)
                        elif key == 'regimens':
                            for i in range(1,len(row)):
                                condition.addRegimen(row[i])
                        elif key == 'dx-tx':
                            for i in range(1,len(row)):
                                condition.addDxTx(row[i])
                        print "Key = %s, value = %s" % (key, value)
                    elif len(row) == 1:
                        print "Row = %s" % (row[0])
                        continue

                else:
                    blankRowFound = True

                if blankRowFound and conditionFound:
                    blankRowFound = False
                    conditionFound = False
                    condition1 = condition2 = condition3 = None
                    breadcrumb1 = breadcrumb2 = breadcrumb3 = None

    finally:
        csvf.close()

    for condition in conditionStore:
        condition.write_html_files()





def initDirs():
    global genPath
    """Builds directory structure"""
    if not os.path.exists(genPath):
        os.mkdir(genPath)
        print "Creating gen root path " + genPath + "..."
    else:
        print "Gen path " + genPath + " exists..."

    print "Creation of directories complete."



if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument('-t', '--tables', help='CSV table data file')
    parser.add_argument('-m', '--metadata', help='Metadata file')

    args = parser.parse_args()

    initDirs()
    try:
        import_regimen_table_data("input/table-data.txt")
        import_condition_data("input/cqp-metadata.txt")
        create_condition_map("gen/condition-content-map.txt")
    except KeyboardInterrupt:
        pass

    # if args.table:
    #     try:
    #         import_table_data("input/table-data.txt")
    #         import_condition_data("metadata/cqp-metadata.txt")
    #     except KeyboardInterrupt:
    #         pass
