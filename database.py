"""
Databases are basically read-only lists of codes read from an xml, which adds extra information to the manager.
"""
from lxml import etree
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codelist import CodeList
from codeeditor import HandleCodeOpen
from common import CountCheckedCodes, SelectItems
from widgets import ModdedTreeWidgetItem, ModdedSubWindow


class Database(QtWidgets.QWidget):
    def __init__(self, name):
        super().__init__()

        # Create the Database Browser and connect it to the handlers
        self.DBrowser = QtWidgets.QTreeWidget()
        self.DBrowser.itemSelectionChanged.connect(self.HandleSelection)
        self.DBrowser.itemDoubleClicked.connect(HandleCodeOpen)

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
        self.SearchBar.textEdited.connect(self.HandleSearch)

        # Add the opened codelist combo box
        self.Combox = QtWidgets.QComboBox()
        self.Combox.addItem('Create New Codelist')

        # Finally, add the "Add" button
        self.AddButton = QtWidgets.QPushButton('Add to Codelist')
        self.AddButton.setEnabled(False)
        self.AddButton.clicked.connect(self.HandleAdd)

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
        # TODO: READ GAME ID FROM A TITLE DATABASE AND GET CORRESPONDING NAME
        try:
            self.gameID = tree.xpath('gameid')[0].text
            self.gameName = tree.xpath('gamename')[0].text
        except:
            self.gameID = 'UNKW00'  # Failsafe
            self.gameName = 'Unknown Game'
        self.setWindowTitle('Database Browser - {} [{}]'.format(self.gameName, self.gameID))

        # Import the codes
        self.ParseDatabase(tree.xpath('category') + tree.xpath('code'), None, 3)  # The second tree is because there can be codes without a category

    def ParseDatabase(self, tree, parent, depth):
        """
        Recursively create the code tree based on the xml
        """
        for entry in tree:
            newitem = ModdedTreeWidgetItem(entry.attrib['name'], False, False)  # Assume it's not a category, codes are more common

            # Determine parenthood
            if parent:
                parent.addChild(newitem)
            else:
                self.DBrowser.addTopLevelItem(newitem)

            # Determine type of entry
            if entry.tag == 'category':
                newitem.setAsCategory(True)
                self.ParseDatabase(entry, newitem, depth + 1)
            elif entry.tag == 'code':
                newitem.setText(1, entry[0].text[1:-depth].upper())
                newitem.setText(2, entry.attrib['comment'])
                newitem.setText(3, str([(pl.attrib['letter'],
                                         int(pl.attrib['type']),
                                         pl.attrib['comment'],
                                         pl.attrib['args'].split(',')) for pl in entry.xpath('placeholder')]))

    def HandleSelection(self):
        # Do the selection
        SelectItems(self.DBrowser)

        # Update the Add button
        if CountCheckedCodes(self.DBrowser, True):
            self.AddButton.setEnabled(True)
        else:
            self.AddButton.setEnabled(False)

    def HandleSearch(self, text):
        """
        Filters codes based on a given string
        """
        for item in self.DBrowser.findItems('', Qt.MatchContains | Qt.MatchRecursive):
            item.setHidden(True)  # Hide all items
            if text.lower() in item.text(0).lower() and item.text(1):
                item.setHidden(False)  # Unhide the item if it's a code and it the text matches, then unhide its parents
                self.UnhideParent(item)

    def UnhideParent(self, item):
        """
        Recursively unhides a given item's parents
        """
        if item.parent():
            item.parent().setHidden(False)
            self.unhideParent(item.parent())

    def HandleAdd(self):
        """
        Transfers the selected codes to the chosen codelist
        """
        enabledlist = CountCheckedCodes(self.DBrowser, True)
        if self.Combox.currentIndex() > 0:
            for window in globalstuff.mainWindow.mdi.subWindowList():
                if isinstance(window.widget(), CodeList) and window.windowTitle() == self.Combox.currentText():
                    window.widget().AddFromDatabase(enabledlist)
                    return
        else:
            win = ModdedSubWindow()
            win.setWidget(CodeList('New Code List'))
            win.widget().AddFromDatabase(enabledlist)
            win.widget().gidInput.setText(self.gameID)
            win.setAttribute(Qt.WA_DeleteOnClose)
            globalstuff.mainWindow.mdi.addSubWindow(win)
            globalstuff.mainWindow.updateboxes()
            win.show()