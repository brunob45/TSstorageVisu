import sys
from PyQt5.QtWidgets import (QWidget, QDialog, QMenuBar,
    QDialogButtonBox, QApplication, QTabWidget, QTableWidget,
    QVBoxLayout, QMenu, QHeaderView, QLabel)
from PyQt5 import QtCore
from PyQt5.QtGui import (QFont, QPalette)
import json

class PageGrid(QTableWidget):
    def __init__(self, title, size, values=None):
        super().__init__()
        self.title = title
        self.setRowCount(size)
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels(['8','7','6','5','4','3','2','1'])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        if values:
            for name, info in values.items():
                if '&' in name:
                    name = name.split('&')[0]
                
                label = QLabel(name)
                label.setAlignment(QtCore.Qt.AlignCenter)

                if 'unused' in name.lower():
                    label.setAutoFillBackground(True)
                    label.setBackgroundRole(QPalette.Dark)

                if info['type'] == 'bits':
                    offset = info['offset']
                    span = info['shape'][1] - info['shape'][0] + 1
                    # if '16' in info['size'] and info['shape'][1] > 8:
                    #     self.setCellWidget(offset, 0, label)
                    #     self.setSpan(offset, info['shape'][0], 1, info['shape'][0]+info['shape'][1]-8)
                    #     offset += 1
                    #     span -= 9
                    #     label = QLabel(name)
                    #     label.setAlignment(QtCore.Qt.AlignCenter)
                    self.setCellWidget(offset, 8-info['shape'][0]-span, label)
                    if span > 1:
                        self.setSpan(offset, 8-info['shape'][0]-span, 1, span)
                elif info['type'] == 'array':
                    span = info['shape'][0]
                    if len(info['shape']) > 1:
                        span *= info['shape'][1]
                    if '16' in info['size']:
                        span *= 2
                    self.setCellWidget(info['offset'], 0, label)
                    self.setSpan(info['offset'], 0, span, 8)
                else:
                    self.setCellWidget(info['offset'], 0, label)
                    if '08' in info['size']:
                        self.setSpan(info['offset'], 0, 1, 8)
                    else:
                        self.setSpan(info['offset'], 0, 2, 8)


    def width(self):
        return self.columnCount() * self.columnWidth(0)
    def contextMenuEvent(self, event):
        menu = QMenu(self)

        selection = self.selectedIndexes()
        minRow = selection[0].row()
        maxRow = selection[0].row()
        minCol = selection[0].column()
        maxCol = selection[0].column()
        for item in selection:
            if item.row() < minRow:
                minRow = item.row()
            if item.row() > maxRow:
                maxRow = item.row()
                
            if item.column() < minCol:
                minCol = item.column()
            if item.column() > maxCol:
                maxCol = item.column()
        
        if minRow != maxRow:
            menu.addAction("Merge rows " + str(minRow+1) + " to " + str(maxRow+1), self.mergeRows)
        elif minCol != maxCol:
            menu.addAction("Merge columns " + str(minCol+1) + " to " + str(maxCol+1), self.mergeCells)
        else:
            menu.addAction("Reset span", self.removeSpan)

        menu.exec(event.globalPos())
    
    def removeSpan(self):
        selection = self.selectedIndexes()
        y = selection[0].row()
        x = selection[0].column()
        self.setSpan(y, x, 1, 1)

    def mergeCells(self):
        model = self.model()
        selection = self.selectedIndexes()
        y = selection[0].row()
        x1 = selection[0].column()
        x2 = selection[-1].column()

        # Clear values
        for index in selection:
            if index.row() != y or index.column() != x1:
                model.setData(index, None)

        self.setSpan(y, x1, 1, x2+1 - x1)

    def mergeRows(self):
        model = self.model()
        selection = self.selectedIndexes()
        y1 = selection[0].row()
        y2 = selection[-1].row()

        # Clear values
        for y in range(y1, y2+1):
            for x in range(self.columnCount()):
                index = model.index(x, y)
                if index.row() != y1 or index.column() != 0:
                    print(index.row(), index.column())
                    model.setData(index, None)

        self.setSpan(y1, 0, y2+1 - y1, self.columnCount())

class PageTabs(QTabWidget):
    def __init__(self, pages):
        super().__init__()
        for title, info in pages.items():
            size = info['size']
            values = info['values']
            self.addTab(PageGrid(title, size, values), title)
            
    def __getitem__(self, index):
        if index >= self.count():
            raise StopIteration
        else:
            return self.widget(index)

    def width(self):
        return self.widget(0).width()

class StorageManagerDialog(QDialog):
    
    def __init__(self):
        super().__init__()
        
        self.initUI()
        
        
    def initUI(self):
        try:
            with open(sys.argv[1], 'r') as f:
                data = json.load(f)
                self.tabs = PageTabs(data['pages'])

        except:
            self.tabs = PageTabs(["configPage2"])

        buttonBox = QDialogButtonBox()
        buttonBox.addButton("Export", QDialogButtonBox.AcceptRole)
        buttonBox.addButton("Exit", QDialogButtonBox.RejectRole)
        buttonBox.addButton("Reset", QDialogButtonBox.ResetRole)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(self.tabs)
        mainLayout.addWidget(buttonBox)
        
        self.setGeometry(200, 200, self.tabs.width()+150, 1000)
        self.setWindowTitle('Storage Manager')    
        self.show()
    
    def accept(self):
        unused_counter = 1
        for tab in self.tabs:
            model = tab.model()
            for row in range(tab.rowCount()):
                name = ""
                counter = 1
                for column in range(tab.columnCount()):
                    value = model.data(model.index(row, column))
                    if value != None:
                        if name != "":
                            print(name + ":" + str(counter))
                            counter = 1
                        name = value
                    else:
                        counter += 1
                if counter > 1:
                    if name == "":
                        print("unused" + str(unused_counter))
                        unused_counter += 1
                    elif counter >= 8:
                        print(name)
                    else:
                        print(name + ":" + str(counter))

                print('---')
        
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = StorageManagerDialog()
    sys.exit(app.exec_())