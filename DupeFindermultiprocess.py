

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QTimer, QRunnable, QThreadPool
import hashlib
import glob
import shutil
import multiprocessing
import sys
import math
import time

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


    def run(self):

        # Initialise the runner function with passed args, kwargs.
        
        self.fn(*self.args, **self.kwargs)

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

    def flush(self):
        pass


class Ui_Dialog(object):
    inFolder = ""
    outFolder = ""

    def __init__(self, parent=None, **kwargs):
        self.threadpool = QThreadPool()
        # Install the custom output stream for PyQt5
        if len(sys.argv) == 1:
            sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)



    def __del__(self):
        # Restore sys.stdout
        sys.stdout = sys.__stdout__

    def start(self):
        print("starting")
        self.runChecker()
        print("finished")

    def threader(self):
        # Pass the function to execute
        worker = Worker(self.start)
        # Execute
        self.threadpool.start(worker)

    def normalOutputWritten(self, text):
        """Append text to the QTextEdit."""
        # Maybe QTextEdit.append() works as well, but this is how I do it:
        cursor = self.plainTextEdit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.plainTextEdit.setTextCursor(cursor)
        self.plainTextEdit.ensureCursorVisible()

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
        self.pushButton.clicked.connect(self.start)
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
        files = []
        if len(sys.argv) == 1:
            path = self.inFolder
            outpath = self.outFolder
        else:
            path = sys.argv[1] + "/"
            outpath = sys.argv[2] + "/"

        nprocs = multiprocessing.cpu_count()
        for file in glob.glob(path + "*.*"):
            files.append(file)

        chunksize = int(math.ceil(len(files) / float(nprocs)))
        procs = []
        out_q = multiprocessing.SimpleQueue()

        for i in range(nprocs):
            p = multiprocessing.Process(
                target=checker,
                args=(files[chunksize * i:chunksize * (i + 1)], out_q))
            procs.append(p)
            p.start()

        map = {}
        lists = []

        for x in range(nprocs):
            lists.append(out_q.get())

        for x in range(nprocs):
            for i in lists[x]:
                if str(i[0:16]) in map:
                    file = i[33:]
                    out = outpath + i[32+len(path):]
                    print('moving dupe to ' + out)
                    shutil.move(file, out)
                else:
                    map[i[0:16]] = i[16:]

    def inputFolderSelect(self):
        Ui_Dialog.inFolder = str(QtWidgets.QFileDialog.getExistingDirectory(None, "Select Directory")+"/")
        self.startpath.setText(Ui_Dialog.inFolder)

    def outputFolderSelect(self):
        Ui_Dialog.outFolder = str(QtWidgets.QFileDialog.getExistingDirectory(None, "Select Directory")+"/")
        self.wheretopath.setText(Ui_Dialog.outFolder)


def checker(files, inQ):
    # push a list of file:md5 to shared queue
    md5s = []
    for file in files:

        md5_returned = generate_file_md5(file)
        md5s.append(md5_returned + " " + file)
    inQ.put(md5s)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)
    if len(sys.argv) == 1:
        Dialog.show()
    else:
        ui.runChecker()
    sys.exit(app.exec_())
    exit()
