

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRunnable, QThreadPool, QTimer
import hashlib
import glob
import shutil
import time
import multiprocessing
import sys
import math


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


def generate_file_md5(filepath, blocksize=128*2**20):
    # function to take a file, and stream it per 10mbit to calculate the md5 rather than loading HUGE file into ram
    m = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while True:
                buf = f.read(blocksize)
                if not buf:
                    break
                m.update(buf)
        return m.hexdigest()
    except IOError:
        print("FILEIO error!")
        return 0


def fileChecker(inp, outp, cores, doneq):
    # make our list of files and set duplicates to 0
    files = []
    dupes = 0

    # detect GUI or CLI and set parameters
    if len(sys.argv) == 1:
        path = inp
        outpath = outp
        nprocs = cores
    else:
        path = sys.argv[1] + "/"
        outpath = sys.argv[2] + "/"
        if sys.argv[3] > multiprocessing.cpu_count() or sys.argv[3] < 1 :
            nprocs = 1
        else:
            nprocs = sys.argv[3]

    # Find all of the files using glob
    for file in glob.glob(path + "*.*"):
        files.append(file)
    print("Found " + str(len(files)) + " files" + "\nchecking files! this might take some time.")
    doneq.put(35)
    # split up work based on the number of cores selected
    chunksize = int(math.ceil(len(files) / float(nprocs)))
    procs = []
    out_q = multiprocessing.Queue()

    # spawn child processes to crunch our md5s for each file
    for i in range(nprocs):
        p = multiprocessing.Process(target=checker, args=(files[chunksize * i:chunksize * (i + 1)], out_q, doneq, len(files)))
        procs.append(p)
        p.start()

    md5map = {}
    lists = []
    # build list from our child processes
    for x in range(nprocs):
        lists.append(out_q.get())
    for x in range(nprocs):
        # for each process that exists
        for i in lists[x]:
            # Read its list of file:md5 to see if it is in the map
            if str(i[0:16]) in md5map:
                # if found in map, move to duplicate folder, increase duplicate count
                dupes += 1
                file = i[33:]
                out = outpath + i[33+len(path):]
                shutil.move(file, out)
                # add some progress to our progress bar
                if doneq.full():
                    while doneq.full():
                        time.sleep(.1)
                doneq.put(65 / len(files))
            else:
                # if not found in map, add to map for quick searching later
                md5map[i[0:16]] = i[16:]
                # add some progress to our progress bar
                if doneq.full():
                    print("full Q")
                    continue
                else:
                    doneq.put(65 / len(files))
    for p in procs:
        p.join()
    doneq.put(100)
    print("found " +str(dupes) + " duplicates, moving files and cleaning up!")


class EmittingStream(QtCore.QObject):
    # Create emitter to let our GUI know whenever something is printed
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
        # Install the custom output stream for PyQt5, but nor for CLI
        # create our multiprocess queue to track progress bar amount
        self.done_q = multiprocessing.Queue()
        self.done_q.maxsize = 1024

        if len(sys.argv) == 1:
            sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)

    def __del__(self):
        # Restore sys.stdout
        sys.stdout = sys.__stdout__

    def start(self):
        # function that worker thread executes
        fileChecker(self.inFolder, self.outFolder, self.coresSelector.value(), self.done_q)


    def threader(self):
        # make worker thread
        # Pass the function to execute
        self.progressBar.setValue(0)
        if self.inFolder == "" or self.outFolder == "":
            print("make sure to select the folders!")
            return
        print("starting")
        print("Using " + str(self.coresSelector.value()) + " cores")
        self.worker = Worker(self.start)
        # Execute
        self.threadpool.start(self.worker)
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateProgbar)
        self.timer.start(10)

    def normalOutputWritten(self, text):
        # Append text to the QTextEdit.
        cursor = self.plainTextEdit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.plainTextEdit.setTextCursor(cursor)
        self.plainTextEdit.ensureCursorVisible()

    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(587, 418)

        self.coresSelector = QtWidgets.QSpinBox(Dialog)
        self.coresSelector.setGeometry(QtCore.QRect(500, 70, 42, 22))
        self.coresSelector.setMinimum(1)
        self.coresSelector.setMaximum(multiprocessing.cpu_count()-1)
        self.coresSelector.setObjectName("spinBox")

        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(500, 50, 47, 13))
        self.label.setObjectName("label")

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

        self.progressBar = QtWidgets.QProgressBar(Dialog)
        self.progressBar.setGeometry(QtCore.QRect(130, 340, 300, 23))
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        self.pushButton.clicked.connect(self.threader)
        self.input.clicked.connect(self.inputFolderSelect)
        self.output.clicked.connect(self.outputFolderSelect)


    def retranslateUi(self, Dialog):
        # text on widgets
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "DuperFinder 9001"))
        self.pushButton.setText(_translate("Dialog", "Find dupes!"))
        self.startpath.setText(_translate("Dialog", "Please select a folder"))
        self.wheretopath.setText(_translate("Dialog", "Please select an output folder"))
        self.input.setText(_translate("Dialog", "select folder"))
        self.output.setText(_translate("Dialog", "Output folder"))
        self.label.setText(_translate("Dialog", "Cores"))

    def inputFolderSelect(self):
        # save path from selection dialogue
        Ui_Dialog.inFolder = str(QtWidgets.QFileDialog.getExistingDirectory(None, "Select Directory")+"/")
        self.startpath.setText(Ui_Dialog.inFolder)

    def outputFolderSelect(self):
        # save path from selection dialogue
        Ui_Dialog.outFolder = str(QtWidgets.QFileDialog.getExistingDirectory(None, "Select Directory")+"/")
        self.wheretopath.setText(Ui_Dialog.outFolder)

    def updateProgbar(self):

        if self.done_q.empty():
            pass
        progress = self.done_q.get()
        if progress+self.progressBar.value() >= 100:
            self.progressBar.setValue(100)
            self.timer.stop()
            print("finished!")
            return
        else:
            self.progressBar.setValue((progress+self.progressBar.value()))


def checker(files, inQ, doneq, total):
    # push a list of dict file:md5 to shared queue
    prog = 0
    md5s = []
    for file in files:
        md5_returned = generate_file_md5(file)
        md5s.append(md5_returned + " " + file)

        if doneq.full():
            print("full Q!")
            time.sleep(.1)
        else:
            prog += (65/total)

        if prog > 1:
            doneq.put(prog)
            prog = 0

    inQ.put(md5s)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    if len(sys.argv) == 1:
        Dialog.show()
    else:
        ui.threader()
    sys.exit(app.exec_())


