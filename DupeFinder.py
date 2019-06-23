

from PyQt5 import QtCore, QtGui, QtWidgets
import hashlib
import glob
import shutil
import multiprocessing


def generate_file_md5(filepath, blocksize=64*2**20):
    # function to take a file, and stream it bit by bit to calculate the md5 rather than loading HUGE file into ram
    m = hashlib.md5()
    with open(filepath, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update( buf )
    return m.hexdigest()


class EmittingStream(QtCore.QObject):

    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))


class Ui_Dialog(object):
    inFolder = ""
    outFolder = ""

    def __init__(self, parent=None, **kwargs):

        # Install the custom output stream for PyQt5
        sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)

    def __del__(self):
        # Restore sys.stdout
        sys.stdout = sys.__stdout__

    def normalOutputWritten(self, text):
        """Append text to the QTextEdit."""
        # Maybe QTextEdit.append() works as well, but this is how I do it:
        cursor = self.plainTextEdit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.plainTextEdit.setTextCursor(cursor)
        self.plainTextEdit.ensureCursorVisible()

    @staticmethod
    def checker(path, moveto):
        files = []

        for file in glob.glob(path + "*.*"):
            files.append(file)
        # keep a map of md5 hashes to quickly find duplicates if we have seen them before
        md5s = {}
        for file in files:

            md5_returned = generate_file_md5(file)
            print(file[len(path):] + " "+ md5_returned)

            if md5_returned in md5s:
                print('moving dupe to ' + moveto + file[len(path):])

                shutil.move(file, moveto + file[len(path):])
            else:
                md5s[md5_returned] = file

    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(587, 418)
        self.pushButton = QtWidgets.QPushButton(Dialog)
        self.pushButton.setGeometry(QtCore.QRect(230, 380, 75, 23))
        self.pushButton.setObjectName("pushButton")
        self.plainTextEdit = QtWidgets.QPlainTextEdit(Dialog)
        self.plainTextEdit.setGeometry(QtCore.QRect(30, 20, 461, 131))
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.startpath = QtWidgets.QLineEdit(Dialog)
        self.startpath.setGeometry(QtCore.QRect(50, 230, 321, 20))
        self.startpath.setObjectName("startpath")
        self.wheretopath = QtWidgets.QLineEdit(Dialog)
        self.wheretopath.setGeometry(QtCore.QRect(50, 280, 321, 20))
        self.wheretopath.setObjectName("wheretopath")
        self.input = QtWidgets.QPushButton(Dialog)
        self.input.setGeometry(QtCore.QRect(380, 230, 75, 23))
        self.input.setObjectName("input")
        self.output = QtWidgets.QPushButton(Dialog)
        self.output.setGeometry(QtCore.QRect(380, 280, 75, 23))
        self.output.setObjectName("output")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        self.pushButton.clicked.connect(self.runChecker)
        self.input.clicked.connect(self.inputFolderSelect)
        self.output.clicked.connect(self.outputFolderSelect)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "DuperFinder 9001"))
        self.pushButton.setText(_translate("Dialog", "Find dupes!"))
        self.startpath.setText(_translate("Dialog", "Please select a folder"))
        self.wheretopath.setText(_translate("Dialog", "Please select an output folder"))
        self.input.setText(_translate("Dialog", "select folder"))
        self.output.setText(_translate("Dialog", "Output folder"))

    def runChecker(self):
        self.checker(Ui_Dialog.inFolder, Ui_Dialog.outFolder)

    def inputFolderSelect(self):
        Ui_Dialog.inFolder = str(QtWidgets.QFileDialog.getExistingDirectory(None, "Select Directory")+"/")
        self.startpath.setText(Ui_Dialog.inFolder)



    def outputFolderSelect(self):
        Ui_Dialog.outFolder = str(QtWidgets.QFileDialog.getExistingDirectory(None, "Select Directory")+"/")
        self.wheretopath.setText(Ui_Dialog.outFolder)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
