#!/usr/bin/env python


import formatter, htmllib, locale, os, StringIO, re, readline, tempfile, zipfile
import json
import csv


from bs4 import BeautifulSoup

locale.setlocale(locale.LC_ALL, 'en_US.utf-8')

basedir = ''
genPath = 'gen'
tempPath = 'temp'
chaps = None
headingsStore = {}          # store metadata for all headings found in EPUB
regimenStore = {}             # store metadata for tables
conditionStore = []               # store condition for Condition Quick Pick feature
imageMap = {}
REPLACE_IMAGE_WITH_HTML_TAG = "replace-image-with-html"
REPLACE_IMAGE_WITH_CONDITION_TAG = "replace-image-with-condition"

BACK_BUTTON_ANCHOR_ATTRIBUTES = '''class="ui-btn ui-icon-back ui-btn-icon-notext ui-corner-all" aria-label="back"'''
MENU_BUTTON_ANCHOR_ATTRIBUTES = '''class="ui-btn ui-icon-bars ui-btn-icon-notext ui-corner-all" aria-label="main menu"'''


class Breadcrumb():
    def __init__(self, text, link):
        self.text = text
        self.link = link


class ImageFile():
    (REMOVE,USE,CONDITION_REPLACE, HTML_REPLACE) = (0, 1, 2, 3)

    def __init__(self, image_file):
        self.file = image_file
        self.replaceWithConditionTables = []
        self.replaceWithHtmlFile = None
        self.command = None

    def use(self):
        self.command = ImageFile.USE

    def remove(self):
        self.command = ImageFile.REMOVE

    def replaceWithCondition(self):
        self.command = ImageFile.CONDITION_REPLACE

    def replaceWithHtml(self):
        self.command = ImageFile.HTML_REPLACE

    def __repr__(self):
        return "ImageFile(file=%r,command=%r, tables=%r)" % (self.file,self.command,self.replaceWithConditionTables)


def write_back_button_anchor(f, dest_link):
    f.write('''<a href="''')
    f.write(dest_link)
    f.write('''" ''')
    f.write(BACK_BUTTON_ANCHOR_ATTRIBUTES)
    f.write('''></a>''')


def write_menu_button_anchor(f):
    f.write('''<a href="#nav-panel" ''')
    f.write(MENU_BUTTON_ANCHOR_ATTRIBUTES)
    f.write('''></a>''')


def write_menu_panel(f):
    f.write('''
        <div data-role="panel" data-display="push" data-theme="b" id="nav-panel">
            <ul data-role="listview">
                <li data-icon="delete"><a href="#" data-rel="close">Close menu</a></li>
                <li><a href="../conditions/c0-clv.html">Condition Quick Pick</a></li>
                <li><a href="../guidelines/lv-0.html">Full STD Tx Guidelines</a></li>
                <li><a href="../page/hx-pdf.html">Taking a Sexual Hx PDF</a></li>
                <li><a href="../terms/1.html">Terms and Abbreviations</a></li>
                <li><a href="../refs/lv-0.html">References</a></li>
                <li><a href="../page/about_us.html">About Us</a></li>
            </ul>
        </div><!-- /panel -->
    ''')


#region Common Head for HTML files
def write_guidelines_common_head(f, title):
    f.write('''<!DOCTYPE html>
<html>
    <head>
        <title>''')

    f.write(title)

    f.write('''</title>
    </head>''')

#endregion
def write_guidelines_breadcrumbs(html_file, headingId):

    # do not write breadcrumbs for root condition
    if headingId != 0:
        breadcrumbs = []
        currentHeadingId = headingId

        # put heading's listview into breadcrumbs
        if heading_has_children(headingId) and heading_has_text(headingId):
            text = get_heading_title(headingId)
            link = get_heading_listview_link(headingId)
            breadcrumb = Breadcrumb(text, link)
            breadcrumbs.append(breadcrumb)

        while currentHeadingId != 0:
            parentId = get_heading_parent(currentHeadingId)
            text = get_heading_title(parentId)
            link = get_heading_parent_listview_link(currentHeadingId)
            breadcrumb = Breadcrumb(text, link)
            breadcrumbs.append(breadcrumb)
            currentHeadingId = parentId

        breadcrumbs.reverse()

        html_file.write('''
            <div id=guidelines_breadcrumbs>
            ''')
        if len(breadcrumbs):
            for index, breadcrumb in enumerate(breadcrumbs):
                assert isinstance(breadcrumb, Breadcrumb)

                html_file.write('''
                    <a href="''')
                html_file.write(breadcrumb.link)
                html_file.write('''" >''')
                html_file.write(breadcrumb.text)
                html_file.write('''</a>''')

                html_file.write('<span class="carrot"> > </span>')

        if heading_has_children(headingId) and heading_has_text(headingId):
            html_file.write("Overview")
        else:
            html_file.write(get_heading_title(headingId))

        html_file.write('''
            </div>
            </br>''')


def write_guidelines_listview_breadcrumbs(html_file, headingId):

    # do not write breadcrumbs for root condition
    if headingId != 0:
        breadcrumbs = []
        currentHeadingId = headingId

        while currentHeadingId != 0:
            parentId = get_heading_parent(currentHeadingId)
            text = get_heading_title(parentId)
            link = get_heading_parent_link(currentHeadingId)
            breadcrumb = Breadcrumb(text, link)
            breadcrumbs.append(breadcrumb)
            currentHeadingId = parentId

        breadcrumbs.reverse()

        html_file.write('''
            </br>
            <div id=guidelines_listview_breadcrumbs>
            ''')
        if len(breadcrumbs):
            for index, breadcrumb in enumerate(breadcrumbs):
                assert isinstance(breadcrumb, Breadcrumb)

                html_file.write('''
                    <a href="''')
                html_file.write(breadcrumb.link)
                html_file.write('''" >''')
                html_file.write(breadcrumb.text)
                html_file.write('''</a>''')

                html_file.write(' > ')

        html_file.write(get_heading_title(headingId))

        html_file.write('''
            </div>
            </br>''')


def write_guidelines_page_body_start(f, headingId):
    global headingsStore
    f.write('''
    <body>
        <!-- Start of page -->
        <div data-role="page" id="''')

    pageId = "g%s" % headingId
    f.write(pageId)

    f.write('''" data-theme="a">
            <div data-role="header" data-id="guidelines-header" data-theme="b" data-position="fixed">
                ''')
    write_back_button_anchor(f, get_heading_parent_listview_link(headingId))
    f.write('''
                <h3>STD Tx Guidelines</h3>
                ''')
    write_menu_button_anchor(f)

    #print headingsStore[headingId]

    f.write('''
            </div>
            <div data-role="content">''')

    write_guidelines_breadcrumbs(f, headingId)


def write_guidelines_page_body_end(f, headingId):
    f.write('''
            </div>''')
    write_menu_panel(f)
    f.write('''
        </div>
        <!-- end of guidelines heading page -->
    </body>
</html>
    ''')


def get_heading_parent(headingId):
    return headingsStore[headingId]['parent']

def get_heading_title(headingId):
    return headingsStore[headingId]['title']

def get_heading_level(headingId):
    return headingsStore[headingId]['level']

def heading_has_children(headingId):
    state = headingsStore[headingId]['hasChildren']

    return headingsStore[headingId]['hasChildren']

def heading_has_text(headingId):
    state = headingsStore[headingId]['hasText']
    return state

def get_heading_children(headingId):
    return headingsStore[headingId]['children']

def get_heading_parent_link(headingId):
    parentId = get_heading_parent(headingId)
    link = "lv-%d.html" % parentId
    return link

def get_heading_listview_link(headingId):
    link = "lv-%d.html" % headingId
    return link

def get_heading_parent_listview_link(headingId):
    # if heading has text then parent link is it's own listview
    if heading_has_text(headingId) and heading_has_children(headingId):
        link = "lv-%d.html" % headingId
    else:
        parentId = get_heading_parent(headingId)
        link = "lv-%d.html" % parentId
    return link

def get_heading_child_link(childId):
    if heading_has_children(childId) is True:
        link = "lv-%d.html" % childId
    else:
        link = "%d.html" % childId
    return link

def get_heading_overview_link(headingId):
    link = "%d.html" % headingId
    return link


def textify(html_snippet):
    ''' text dump of html '''
    class Parser(htmllib.HTMLParser):
        def anchor_end(self):
            self.anchor = None

    class Formatter(formatter.AbstractFormatter):
        pass

    class Writer(formatter.DumbWriter):
        def __init__(self, fl):
            formatter.DumbWriter.__init__(self, fl)
        def send_label_data(self, data):
            self.send_flowing_data(data)
            self.send_flowing_data(' ')

    o = StringIO.StringIO()
    p = Parser(Formatter(Writer(o)))
    p.feed(html_snippet)
    p.close()

    return o.getvalue()

def table_of_contents(fl):
    global basedir

    # find opf file
    soup = BeautifulSoup(fl.read('META-INF/container.xml'))
    opf = dict(soup.find('rootfile').attrs)['full-path']

    basedir = os.path.dirname(opf)
    print "Base Directory = %s" % basedir
    if basedir:
        basedir = '{0}/'.format(basedir)

    soup =  BeautifulSoup(fl.read(opf))

    # title
    yield (soup.find('dc:title').text, None)

    # all files, not in order
    print("Printing all files:")
    x, ncx = {}, None
    for item in soup.find('manifest').findAll('item'):
        d = dict(item.attrs)
        x[d['id']] = '{0}{1}'.format(basedir, d['href'])
        if d['media-type'] == 'application/x-dtbncx+xml':
            ncx = '{0}{1}'.format(basedir, d['href'])
            print ("Table of contents file = %s" % ncx)


    # reading order, not all files
    print ("Printing files in order:")
    y = []
    for item in soup.find('spine').findAll('itemref'):
        y.append(x[dict(item.attrs)['idref']])

    z = {}
    if ncx:
        # get titles from the toc
        soup =  BeautifulSoup(fl.read(ncx))

        for navpoint in soup('navpoint'):
            k = navpoint.content.get('src', None)
            # strip off any anchor text
            k = k.split('#')[0]
            if k:
                z[k] = navpoint.navlabel.text

    # output
    for section in y:
        if section in z:
            yield (z[section].encode('utf-8'), section.encode('utf-8'))
        else:
            yield (u'', section.encode('utf-8').strip())

def list_chaps(chaps):

    print "Listing chapters"
    for i, (title, src) in enumerate(chaps):
        print "Source file = %s " % src
    return i

def check_epub(fl):
    if os.path.isfile(fl) and os.path.splitext(fl)[1].lower() == '.epub':
        return True

def dump_epub(fl):
    if not check_epub(fl):
        return
    fl = zipfile.ZipFile(fl, 'r')
    chaps = [i for i in table_of_contents(fl)]
    for title, src in chaps:
        print title
        print '-' * len(title)
        if src:
            soup = BeautifulSoup(fl.read(src))
            print unicode(soup.find('body')).encode('utf-8')
        print '\n'

def parse_epub(fl):
    global chaps

    if not check_epub(fl):
        print "Bad EPUB file."
        return

    fl = zipfile.ZipFile(fl, 'r')
    chaps = [i for i in table_of_contents(fl)]

    list_chaps(chaps)


def write_heading_content(headingId):
    # write current heading, and content between current and next heading
    # to heading content file as HTML using heading ID as name
    with open("page/headings/" + str(headingId) + ".html", "w") as hidf:

        try:

            write_guidelines_common_head(hidf, "STD Tx Guidelines")
            write_guidelines_page_body_start(hidf, headingId)

            # read in raw content from temp file and write it to heading content file
            with open("temp/heading-content-raw/" + str(headingId) + ".html", "r") as thcf:
                try:

                    ## Read the first line
                    line = thcf.readline()

                    ## search for replace image tags
                    while line:
                        if REPLACE_IMAGE_WITH_CONDITION_TAG in line:
                            tableId = thcf.readline().strip()
                            regimenTable = regimenStore[tableId]
                            regimenData = regimenTable.readLinesFromTableHtmlFile()
                            hidf.writelines(regimenData)
                            line = thcf.readline()   #read closing cond-table-insert tag
                        elif REPLACE_IMAGE_WITH_HTML_TAG in line:
                            htmlSnippetFileName = thcf.readline().strip()
                            with open("data/html/" + htmlSnippetFileName) as htmlSnippetFile:
                                try:
                                    htmlSnippetData = htmlSnippetFile.readlines()
                                    hidf.writelines(htmlSnippetData)
                                except IOError:
                                    print "Can not open HTML snippet %s for image replacement." % htmlSnippetFileName
                                finally:
                                    htmlSnippetFile.close()

                        else:
                            hidf.write(line)
                        line = thcf.readline()

                except IOError:
                    pass
                finally:
                    thcf.close()

            write_guidelines_page_body_end(hidf, headingId)

        finally:
            hidf.close()


def write_temp_heading_content(headingId, headingTag):
    # write current heading, and content between current and next heading
    # to heading content file as HTML using heading ID as name
    with open("temp/heading-content-raw/" + str(headingId) + ".html", "w") as thcf:

        try:
            thcf.write(headingTag.prettify(formatter="html"))
            sibling = headingTag.findNextSibling(text=None)
            while sibling is not None:
                if sibling.name == 'h1' or sibling.name == 'h2' or sibling.name == 'h3' or\
                   sibling.name == 'h4' or sibling.name == 'h5' or sibling.name == 'h6':
                    break
                else:

                    thcf.write (sibling.prettify(formatter="html"))
                    sibling = sibling.findNextSibling(text=None)

        finally:
            thcf.close()

def write_children_listview_body(f, headingId):

    f.write('''
    <body>
        <div data-role="page" id="''')

    f.write(str(headingId))
    f.write('''" data-theme="a">
  	        <div data-role="header" data-id="guidelines-header" data-theme="b" data-position="fixed">''')

    if get_heading_level(headingId) > 0:
        write_back_button_anchor(f, get_heading_parent_link(headingId))

    f.write('''<h1>STD Tx Guidelines</h1>''')
    write_menu_button_anchor(f)

    f.write('''
            </div>  <!-- end of header div -->
    ''')



    f.write('''
            <div data-role="content" data-theme="a" >''')

    write_guidelines_listview_breadcrumbs(f, headingId)

    f.write('''
                <ul data-count-theme="b" data-role="listview" data-inset="true" data-divider-theme="a">''')

    # if heading has children and text then first
    # item in list is the Overview which is text
    # of current heading
    if heading_has_text(headingId):
        f.write('''

                    <li ><a href="''')
        f.write(get_heading_overview_link(headingId))
        f.write('''">Overview</a></li>''')

    children = get_heading_children(headingId)
    for childId in children:
        print "Child ID = %s" % childId
        title = get_heading_title(childId)
        childLink = get_heading_child_link(childId)
        f.write('''
                    <li ><a href="''')
        f.write(childLink)
        f.write('''"><span style="white-space:normal;">''')
        f.write(title)
        f.write('''</span></a></li>''')

    # write link to parent list view
    f.write('''
                </ul>
            </div>
        ''')
    write_menu_panel(f)
    f.write('''
        </div>
    </body>
</html>

        ''')

def write_children_listview(headingId):
    # write current heading, and content between current and next heading
    # to heading content file as HTML using heading ID as name
    with open("page/headings/lv-" + str(headingId) + ".html", "w") as lvf:

        try:
            write_guidelines_common_head(lvf, 'STD Tx Guidelines')
            write_children_listview_body(lvf, headingId)
        finally:
            lvf.close()

def create_heading_map(fl):
    global genPath
    global headingsStore

    headingId = 1
    h1ListView  = []
    h2ListView  = []
    h3ListView  = []
    h4ListView  = []
    h5ListView  = []
    lastTag = None
    lastLevel = 1

    try:
        # turn file handle into zip file handle
        fl = zipfile.ZipFile(fl, 'r')

        # create a new JSON file that contains all the headings metadata
        with open("content-map.txt", "w") as f:
            try:
                # write root
                headingsStore[0] = {'title':'Full Guidelines', 'level':0, 'parent':None, 'src':None, 'hasText':False, 'hasChildren':True}

                #for each chapter file in the EPUB
                for title, src in chaps:
                    if src:
                        # BeautifulSoup creates a nested data structure that represents
                        # the XHTML chapter file that is in the EPUB document
                        soup = BeautifulSoup(fl.read(src))

                        replace_table_images(soup)

                        # get just the heading tags
                        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
                        for headingTag in headings:
                            if headingTag.name == "h1":
                                level = 1
                                parentId = 0
                                h1ListView.append(headingId)
                            elif headingTag.name == "h2":
                                level = 2
                                h2ListView.append(headingId)
                                # parent is last one in higher level list
                                parentId = h1ListView[-1]
                            elif headingTag.name == "h3":
                                level = 3
                                h3ListView.append(headingId)
                                parentId = h2ListView[-1]
                            elif headingTag.name == "h4":
                                level = 4
                                h4ListView.append(headingId)
                                parentId = h3ListView[-1]
                            elif headingTag.name == "h5":
                                level = 5
                                h5ListView.append(headingId)
                                parentId = h4ListView[-1]
                            elif headingTag.name == "h6":
                                level = 6
                                parentId = h5ListView[-1]
                            elif headingTag.name == "img":
                                print "Found IMG tag."

                            #print "Heading text = " + headingTag.text
                            #print "Heading tag = " + headingTag.name

                            # write out contents of original file
                            # may delete this later as unnecessary
                            htmlFile = os.path.basename(src)
                            htmlFile = os.path.splitext(htmlFile)[0]
                            htmlFile = "temp/orig-file-content/" + htmlFile + ".html"
                            # print "HTML file =", htmlFile

                            # see if heading has text below it
                            sibling = headingTag.findNextSibling(text=None)
                            while sibling is None:
                                sibling = headingTag.findNextSibling(text=None)

                            if sibling.name == 'h1' or sibling.name == 'h2' or sibling.name == 'h3' or\
                               sibling.name == 'h4' or sibling.name == 'h5' or sibling.name == 'h6':
                                headingHasText = False
                            else:
                                headingHasText = True

                            hasChildren = False
                            headingsStore[headingId] = {'title':headingTag.text, 'level':level, 'parent':parentId, 'src':htmlFile, 'hasText':headingHasText, 'hasChildren':hasChildren}

                            if headingHasText:
                                write_temp_heading_content(headingId, headingTag)

                            # modify heading tag with custom attributes
                            headingTag['data-irda-section'] = 'undefined'
                            headingTag['data-irda-condition'] = 'undefined'
                            headingTag['data-irda-hid'] = headingId

                            # write individual file for each heading
                            headingId += 1
                            lastTag = headingTag


                        # done processing chapter file, write it out as HTML
                        with open(htmlFile, "w") as hf:
                            try:
                                hf.write (soup.body.prettify(formatter="html"))
                            finally:
                                hf.close()

                # now that we have post heading information
                # do some post processing
                for parentHeadingId in headingsStore.keys():
                    childHeadings = []
                    for childHeadingId in headingsStore.keys():
                        if get_heading_parent(childHeadingId) == parentHeadingId:
                            childHeadings.append(childHeadingId)
                    if len(childHeadings) != 0:
                        headingsStore[parentHeadingId]['hasChildren'] = True
                        dict = headingsStore[parentHeadingId]
                        dict['children'] = childHeadings
                        headingsStore[parentHeadingId] = dict
                        # print "Parent ID of", parentHeadingId, "has children ", childHeadings
                    else:
                        headingsStore[parentHeadingId]['hasChildren'] = False
                        # print "Parent ID of %d has no children" % (parentHeadingId)

            finally:
                json.dump(headingsStore, f, indent=4)
            f.close()
    except IOError:
        pass

    # now that we have all child heading info
    # create heading listview and heading content files
    for headingId in headingsStore.keys():
        if heading_has_text(headingId):
            write_heading_content(headingId)
        if heading_has_children(headingId):
            write_children_listview(headingId)
            # print "Parent ID of", parentHeadingId, "has children ", childHeadings



def replace_table_images(soup):
    global imageMap

    image_count = 0;

    # get just the image tags
    image_tags = soup.find_all("img")
    for image_tag in image_tags:
        if image_tag.name == "img":
            print "Image tag = %s" % image_tag
            print "Image src = %s" % image_tag['src']

            # look up image in image map
            image_src = image_tag.get('src')
            image_file = imageMap[image_src]

            assert isinstance(image_file, ImageFile)
            if image_file.command == ImageFile.REMOVE:
                image_tag.extract()
                print "remove file"
            elif image_file.command == ImageFile.USE:
                print "use file"
            elif image_file.command == ImageFile.CONDITION_REPLACE:
                for tableId in image_file.replaceWithConditionTables:
                    # print "Table Lines = %r" % lines

                    table_insert_tag = soup.new_tag(REPLACE_IMAGE_WITH_CONDITION_TAG)
                    table_insert_tag.string = tableId
                    image_tag.insert_before(table_insert_tag)
                image_tag.extract()
                #image_tag.replace_with(''.join(lines))
                # print "replace file"
            elif image_file.command == ImageFile.HTML_REPLACE:
                html_insert_tag = soup.new_tag(REPLACE_IMAGE_WITH_HTML_TAG)
                html_insert_tag.string = image_file.replaceWithHtmlFile
                image_tag.insert_before(html_insert_tag)
                image_tag.extract()

            image_count += 1

    # print "Number of IMG tags in EPUB = %d " % image_count


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





def import_table_data(table_file):

    conditionFound = False
    blankRowFound = False

    table_cnt = 0
    try:

        # create a new JSON file that contains all the headings metadata
        with open(table_file, "r") as csvf:
            csvReader = csv.reader(csvf)
            for row  in csvReader:
                if row:
                    blankRowFound = False
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
                            conditionFound  = True
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
                    blankRowFound = True

                if blankRowFound and conditionFound:
                    table_cnt += 1
                    blankRowFound = False
                    conditionFound = False

                    # write out HTML version of table data to file
                    tableData.writeTableTempHtmlFile()
                    # store table data for later processing
                    regimenStore[tableData.tableId] = tableData

    finally:
        print "Table count = %d" % table_cnt
        csvf.close()


#region Common Head for HTML files

#endregion


class Condition():
    def __init__(self, id, parent, text):
        self.id = id
        self.parent = parent
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

    def setParent(self, parentId):
        self.parentId = parentId
    def addChild(self, childCondition):
        self.children.append(childCondition)
        self.hasChildren = True
    def addBreadcrumb(self, breadcrumb):
        self.breadcrumbs.append(breadcrumb)
    def createMyBreadcrumb(self):
        return Breadcrumb(self.text, self.childrenListViewPage)
    def setListViewLevel(self, parentId):
        self.parentId = parentId
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
        with open('conditions/'+ self.childrenListViewPage, "w") as lvf:
            try:
                self.write_condition_common_head(lvf)
                self.write_html_page_header(lvf, self.childrenListViewPageId)
                self.write_children_listview_body(lvf)
            finally:
                lvf.close()
    def write_html_regimens(self):
        # write current heading, and content between current and next heading
        # to heading content file as HTML using heading ID as name
        with open('conditions/' + self.regimensPage, "w") as regf:
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
        with open('conditions/' + self.dxtxPage, "w") as dxtxf:
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

        if self.id != 0:
            write_back_button_anchor(html_file, self.parent.childrenListViewPage)

        html_file.write('''
                <h1>Condition Quick Pick</h1>
        ''')
        write_menu_button_anchor(html_file)
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
                            if REPLACE_IMAGE_WITH_CONDITION_TAG in line:
                                line = sectionf.readline()   #read table ID
                                line = sectionf.readline()   #read closing cond-table-insert tag
                            else:
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
        write_menu_panel(html_file)
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
        write_menu_panel(html_file)
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
        write_menu_panel(html_file)
        html_file.write('''
        </div>
    </body>
</html>
        ''')


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


# reads the image_map.txt file to determine how we handle images in the EPUB. Options are:
#       use - use this image as is
#       rem - remove the image and nothing takes its place
#       rep - replace images with
#
def import_image_map(map_file):

    specified_files = 0
    # open file, read line by line, until blank line found
    with open(map_file, "r") as mapf:
        csvReader = csv.reader(mapf)
        for row  in csvReader:
            if row:
                if row[0][0] == '#':
                    # print "Found comment"
                    continue
                else:
                    fileName = row[0]
                    imageFile = ImageFile(fileName)
                    command = row[1]
                    if command == 'rem':
                        imageFile.remove()
                    elif command == 'use':
                        imageFile.use()
                    elif command == 'cond':
                        imageFile.replaceWithCondition()
                        imageFile.replaceWithConditionTables = row[2:]
                    elif command == 'html':
                        imageFile.replaceWithHtml()
                        imageFile.replaceWithHtmlFile = row[2]

                    imageMap[fileName] = imageFile
                    specified_files += 1
                    print 'New image file object %r' % imageFile
    print "Image_map file specifies %d files." % specified_files

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
    parser.add_argument('-d', '--dump', action='store_true',
        help='dump EPUB to text')
    parser.add_argument('-e', '--epub', help='EPUB file to parse')
    parser.add_argument('-t', '--tables', help='CSV table data file')
    args = parser.parse_args()

    initDirs()
    if args.epub:
        if args.dump:
            dump_epub(args.epub)
        else:
            try:
                import_table_data("metadata/table-data.txt")
                import_image_map("metadata/image_map.txt")
                parse_epub(args.epub)
                create_heading_map(args.epub)
                import_condition_data("metadata/cqp-metadata.txt")
            except KeyboardInterrupt:
                pass


