import sys
from lxml import etree
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt


class ModdedTreeWidget(QtWidgets.QTreeWidget):
    """
    This modded tree widget lets me move codes between subwindows without losing data
    """
    def __init__(self):
        super().__init__()

        # Set flags
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setHeaderHidden(True)
        self.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.SelectedClicked)
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def dragEnterEvent(self, e):
        """
        This forces the widget to accept drops, which would otherwise be rejected due to the InternalMove flag.
        """
        e.accept()

    def dropEvent(self, e):
        """
        This bad hack adds a copy of the source widget's selected items in the destination widget. This is due to PyQt
        clearing the hidden columns, which we don't want.
        """
        src = e.source()
        if src is not self:
            for item in src.selectedItems():
                clone = item.clone()
                clone.setFlags(clone.flags() | Qt.ItemIsEditable)
                self.addTopLevelItem(clone)
        QtWidgets.QTreeWidget.dropEvent(self, e)  # Call the original function


class CodeList(QtWidgets.QWidget):
    """
    Codelists are different from databases, as they accept adding/removing, importing/exporting, reordering, dragging
    and more.
    """
    def __init__(self, wintitle):
        super().__init__()

        # Create the codelist and connect it to the handlers
        self.Codelist = ModdedTreeWidget()
        self.Codelist.itemSelectionChanged.connect(self.handleSelection)
        self.Codelist.itemDoubleClicked.connect(handleCodeOpen)
        self.Codelist.itemChanged.connect(self.renameWindows)

        # Create the menu bar
        self.menuBar = QtWidgets.QMenuBar()
        self.createMenubar(self.menuBar)

        self.addButton = QtWidgets.QPushButton('Add Code')
        self.importButton = QtWidgets.QPushButton('Import List')
        self.removeButton = QtWidgets.QPushButton('Remove Selected')

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addWidget(self.menuBar, 0, 0, 1, 3)
        lyt.addWidget(self.Codelist, 1, 0, 1, 3)
        lyt.addWidget(self.addButton, 2, 0)
        lyt.addWidget(self.importButton, 2, 1)
        lyt.addWidget(self.removeButton, 2, 2)
        self.setLayout(lyt)

        # Set the window title accordingly
        self.handleWinTitle(wintitle)

    def createMenubar(self, bar):
        """
        Sets up the menubar
        """
        # File Menu
        file = bar.addMenu('&File')
        file.addAction('Add Code')
        file.addAction('Import from List')
        file.addAction('Change Game ID')

        # Edit Menu
        edit = bar.addMenu('&Edit')
        sort = edit.addMenu('Sort by...')
        sort.addAction('Alphabetical')
        sort.addAction('Alphabetical (Reverse)')
        sort.addAction('Size')
        edit.addAction('Remove Selected')

        # Code Menu
        code = bar.addMenu('&Code')
        code.addAction('Open in Auto-Porter')
        code.addAction('Open in Disassembler')

    def handleWinTitle(self, wintitle, i=0):
        winlist = [window.windowTitle() for window in mainWindow.mdi.subWindowList() if isinstance(window.widget(), CodeList)]
        while True:
            i += 1
            windowtit = ' '.join([wintitle, str(i)])
            if windowtit not in winlist:
                break
        self.setWindowTitle(windowtit)

    def handleSelection(self):
        """
        Marks items as checked if they are selected, otherwise unchecks them
        """
        bucketlist = self.Codelist.findItems('', Qt.MatchContains | Qt.MatchRecursive)
        for item in bucketlist:
            if item in self.Codelist.selectedItems():
                item.setCheckState(0, Qt.Checked)
            else:
                item.setCheckState(0, Qt.Unchecked)

        for item in bucketlist:
            if item in self.Codelist.selectedItems() and item.childCount() and not item.isExpanded():
                self.checkChildren(item)

    def checkChildren(self, item):
        for i in range(0, item.childCount()):
            child = item.child(i)
            if child.childCount():
                self.checkChildren(child)
            else:
                child.setCheckState(0, Qt.Checked)

    def renameWindows(self):
        """When you rename a code, the program will look for code viewers that originated from that code and update
        their window title accordingly"""
        codelist = [code for code in self.Codelist.findItems('', Qt.MatchContains | Qt.MatchRecursive) if not code.childCount()]
        winlist = [window for window in mainWindow.mdi.subWindowList() if isinstance(window.widget(), CodeViewer) and window.widget().parentz in codelist]
        for window in winlist:
            window.widget().setWindowTitle('Code Viewer - {}'.format(window.widget().parentz.text(0)))

    def addFromDatabase(self, enabledlist):
        header = self.Codelist.header()
        for item in enabledlist:
            clone = item.clone()
            clone.setFlags(clone.flags() | Qt.ItemIsEditable)
            self.Codelist.addTopLevelItem(clone)
            self.setMinimumWidth(header.length() + 70)
            self.cleanChildren(clone)

    def cleanChildren(self, item):
        """
        The clone function duplicates unchecked children as well, so we're cleaning those off. I'm sorry, little ones.
        """
        for i in range(0, item.childCount()):
            child = item.child(i)
            if child:
                child.setFlags(child.flags() | Qt.ItemIsEditable)
                if child.childCount():
                    self.cleanChildren(child)
                else:
                    if child.checkState(0) == Qt.Unchecked:
                        item.takeChild(i)


class CodeViewer(QtWidgets.QWidget):
    """
    A simple window showing the code and its name, author and comment.
    """
    def __init__(self, parent):
        super().__init__()

        # Initialize vars
        self.parentz = parent  # This is named parentz due to a name conflict
        self.name = parent.text(0)
        self.code = parent.text(1)
        self.comment = parent.text(2)
        self.placeholders = parent.text(3)

        # Create the code and comment forms and set the window title
        self.CodeContent = QtWidgets.QPlainTextEdit(self.code)
        self.CodeComment = QtWidgets.QPlainTextEdit(self.comment)
        self.setWindowTitle('Code Viewer - {}'.format(self.name))

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addWidget(self.CodeContent, 0, 0)
        lyt.addWidget(self.CodeComment, 1, 0)
        self.setLayout(lyt)


class Database(QtWidgets.QWidget):
    """
    Databases are basically read-only lists of codes, which provide extra data to the code manager.
    """
    def __init__(self, name):
        super().__init__()

        # Create the Database Browser and connect it to the handlers
        self.DBrowser = QtWidgets.QTreeWidget()
        self.DBrowser.itemSelectionChanged.connect(self.handleSelection)
        self.DBrowser.itemDoubleClicked.connect(handleCodeOpen)

        # Set the proper flags
        self.DBrowser.setHeaderHidden(True)
        self.DBrowser.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)
        self.DBrowser.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        header = self.DBrowser.header()  # The following leaves some space on the right, to allow dragging the selection
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # Add the search bar
        self.SearchBar = QtWidgets.QLineEdit()
        self.SearchBar.setPlaceholderText('Search codes...')
        self.SearchBar.textEdited.connect(self.handleSearch)

        # Add the opened codelist combo box and populate it
        self.Combox = QtWidgets.QComboBox()
        self.Combox.addItem('Create New Codelist')
        updateboxes()

        # Finally, add the "Add" button
        self.AddButton = QtWidgets.QPushButton('Add to Codelist')
        self.AddButton.setEnabled(False)
        self.AddButton.clicked.connect(self.handleAdd)

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addWidget(self.SearchBar, 0, 0, 1, 2)
        lyt.addWidget(self.DBrowser, 1, 0, 1, 2)
        lyt.addWidget(self.Combox, 2, 0)
        lyt.addWidget(self.AddButton, 2, 1)
        self.setLayout(lyt)

        # Open the database
        tree = etree.parse(name).getroot()

        # Parse game id and name, then apply them to the window title
        # TODO: READ GAME ID FROM A TITLE DATABASE AND GET CORRESPONDING NAME, ALSO DON'T CRASH IF NO ID/NAME IS PRESENT
        try:
            self.gameID = tree.xpath('gameid')[0].text
            self.gameName = tree.xpath('gamename')[0].text
        except:
            self.gameID = 'UNKW00'  # Failsafe
            self.gameName = 'Unknown Game'
        self.setWindowTitle('Database Browser - {} [{}]'.format(self.gameName, self.gameID))

        # Import the codes
        self.parseDatabase(tree.xpath('category') + tree.xpath('code'), None, 3)  # The second tree is because there can be codes without a category

    def parseDatabase(self, tree, parent, depth):
        """
        Recursively create the code tree based on the xml
        """
        header = self.DBrowser.header()
        for entry in tree:
            newitem = QtWidgets.QTreeWidgetItem([entry.attrib['name']])
            newitem.setCheckState(0, Qt.Unchecked)
            self.setMinimumWidth(header.length() + 70)

            # Determine parenthood
            if parent:
                parent.addChild(newitem)
            else:
                self.DBrowser.addTopLevelItem(newitem)

            # Determine type of entry
            if entry.tag == 'category':
                newitem.setFlags(newitem.flags() | Qt.ItemIsAutoTristate)
                self.parseDatabase(entry, newitem, depth + 1)
            elif entry.tag == 'code':
                newitem.setFlags(newitem.flags() ^ Qt.ItemIsDropEnabled)
                newitem.setText(1, entry[0].text[1:-depth])
                newitem.setText(2, entry.attrib['comment'])
                plist = []
                for pl in entry.xpath('placeholder'):
                    plist.append(
                        (pl.attrib['letter'], int(pl.attrib['type']), pl.attrib['comment'],
                         pl.attrib['args'].split(','), bool(int(pl.attrib['recursive']))))
                newitem.setText(3, str(plist))

    def handleSearch(self, text):
        """
        Filters codes based on a given string
        """
        for item in self.DBrowser.findItems('', Qt.MatchContains | Qt.MatchRecursive):
            item.setHidden(True)  # Hide all items
            if text.lower() in item.text(0).lower() and not item.childCount():
                item.setHidden(False)  # Unhide the item if it's a code and it matches the query, then unhide its parents
                self.unhideParent(item)

    def unhideParent(self, item):
        """
        Recursively unhides a given item's parents
        """
        if item.parent():
            item.parent().setHidden(False)
            self.unhideParent(item.parent())

    def countCheckedCodes(self):
        """
        Returns a list of the codes currently enabled
        """
        enabledlist = []
        for item in self.DBrowser.findItems('', Qt.MatchContains):
            if item.checkState(0) > 0:  # We're looking for both partially checked and checked items
                enabledlist.append(item)
        return enabledlist

    def handleSelection(self):
        """
        Marks items as checked if they are selected, otherwise unchecks them
        """
        bucketlist = self.DBrowser.findItems('', Qt.MatchContains | Qt.MatchRecursive)
        for item in bucketlist:
            if item in self.DBrowser.selectedItems():
                item.setCheckState(0, Qt.Checked)
            else:
                item.setCheckState(0, Qt.Unchecked)

        for item in bucketlist:
            if item in self.DBrowser.selectedItems() and item.childCount() and not item.isExpanded():
                self.checkChildren(item)

        if len(self.countCheckedCodes()) > 0:
            self.AddButton.setEnabled(True)
        else:
            self.AddButton.setEnabled(False)
        updateboxes()

    def checkChildren(self, item):
        for i in range(0, item.childCount()):
            child = item.child(i)
            if child.childCount():
                self.checkChildren(child)
            else:
                child.setCheckState(0, Qt.Checked)

    def handleAdd(self):
        """
        Transfers the selected codes to the chosen codelist
        """
        enabledlist = self.countCheckedCodes()
        if self.Combox.currentIndex() > 0:
            for window in mainWindow.mdi.subWindowList():
                if isinstance(window.widget(), CodeList) and window.windowTitle() == self.Combox.currentText():
                    window.widget().addFromDatabase(enabledlist)
                    return
        else:
            win = QtWidgets.QMdiSubWindow()
            win.setWidget(CodeList('New Code List'))
            win.widget().addFromDatabase(enabledlist)
            win.setAttribute(Qt.WA_DeleteOnClose)
            win.windowStateChanged.connect(updateboxes)
            mainWindow.mdi.addSubWindow(win)
            win.show()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Create the interface
        self.mdi = QtWidgets.QMdiArea()
        self.setCentralWidget(self.mdi)

        # Create the menubar
        self.createMenubar()

        # Set window title and show the window maximized
        self.setWindowTitle('Code Manager 2')
        self.showMaximized()

    def createMenubar(self):
        """
        Sets up the menubar
        """
        bar = self.menuBar()

        # File Menu
        file = bar.addMenu('&File')
        file.addAction('Exit', self.close)

        # Import menu
        imports = bar.addMenu('&Import')
        imports.addAction('Import Database', self.openDatabase)

    def openDatabase(self):
        """
        Opens a dialog to let the user choose a database.
        """
        name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Database', '', 'Code Database (*.xml)')[0]
        if name:
            win = QtWidgets.QMdiSubWindow()
            win.setWidget(Database(name))
            win.setAttribute(Qt.WA_DeleteOnClose)
            self.mdi.addSubWindow(win)
            win.show()


def updateboxes():
    """
    Looks for opened codelist sub-windows and adds them to each database' combo box
    """
    dblist = [window.widget() for window in mainWindow.mdi.subWindowList() if isinstance(window.widget(), Database)]
    entries = [window.windowTitle() for window in mainWindow.mdi.subWindowList() if isinstance(window.widget(), CodeList)]
    for database in dblist:
        if database.Combox.count() - 1 != len(entries):
            database.Combox.clear()
            database.Combox.addItem('Create New Codelist')
            for window in entries:
                database.Combox.addItem(window)


def handleCodeOpen(item):
    """
    Opens the currently selected code in a new window
    """
    if item and not item.childCount():
        willcreate = True
        for window in mainWindow.mdi.subWindowList():  # Find if there's an existing CodeViewer with same parent and window title
            if isinstance(window.widget(), CodeViewer) and window.widget().parentz == item:
                willcreate = False
                mainWindow.mdi.setActiveSubWindow(window)  # This code was already opened, so let's just set the focus on the existing window
                break
        if willcreate:  # If the code is not already open, go ahead and do it
            win = QtWidgets.QMdiSubWindow()
            win.setWidget(CodeViewer(item))
            win.setAttribute(Qt.WA_DeleteOnClose)
            mainWindow.mdi.addSubWindow(win)
            win.show()


def main():
    global mainWindow  # I fucking hate having to add these lines

    # Start the application
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    ret = app.exec_()

    # Quit the process
    sys.exit(ret)


if __name__ == '__main__':
    main()