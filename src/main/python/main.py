import sys

from cv2 import CAP_PROP_POS_MSEC, VideoCapture
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QShortcut, QHBoxLayout, QPushButton, QVBoxLayout, \
    QWidget, QFileDialog
from fbs_runtime.application_context.PyQt5 import ApplicationContext, cached_property


class AppContext(ApplicationContext):           # 1. Subclass ApplicationContext
    def run(self):                              # 2. Implement run()
        self.main_window.show()
        return self.app.exec_()                 # 3. End run() with this line

    @cached_property
    def main_window(self):
        return MainWindow(self)  # Pass context to the window.

    @cached_property
    def img_corgo(self):
        return QImage(self.get_resource('images/Corgo.jpg'))


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super(MainWindow, self).__init__()
        self.ctx = ctx  # Store a reference to the context for resources, etc.
        self.title = "Giffer"
        self.setWindowTitle(self.title)

        self.init_ui()
        # self.showMaximized()

    def init_ui(self):
        self.add_shortcuts()

        widget = QWidget()
        vLayout = QVBoxLayout()

        corgo = self.add_corgo()
        vLayout.addWidget(corgo)

        layout = QHBoxLayout()
        layout.addWidget(QPushButton('Left'))
        layout.addWidget(QPushButton('Center'))
        layout.addWidget(QPushButton('Right'))
        vLayout.addLayout(layout)

        gifs_layout = QHBoxLayout()
        gifs_layout.addWidget(self.add_corgo())
        gifs_layout.addWidget(self.add_corgo())
        gifs_layout.addWidget(self.add_corgo())
        vLayout.addLayout(gifs_layout)

        self.btn = QPushButton("Select Video")
        self.btn.clicked.connect(self.get_files)
        vLayout.addWidget(self.btn)

        self.video_frames_layout = QHBoxLayout()
        vLayout.addLayout(self.video_frames_layout)

        widget.setLayout(vLayout)
        self.setCentralWidget(widget)

    def add_corgo(self):
        label = QLabel()
        pixmap = QPixmap.fromImage(self.ctx.img_corgo)
        label.setPixmap(pixmap)
        label.setScaledContents(True)

        return label

    def add_shortcuts(self):
        self.quitSc = QShortcut(QKeySequence('Ctrl+W'), self)
        self.quitSc.activated.connect(QApplication.instance().quit)

    def get_files(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setNameFilters(["Source files (*.mov *.mp4)"])

        if dlg.exec_():
            file_name = dlg.selectedFiles()[0]
            images = extract_images(file_name)
            for image in images[:3]:
                pixmap = QPixmap.fromImage(image).scaledToHeight(128)
                picture = LabelClickBorder(pixmap, self)
                picture.pictureClicked.connect(self.get_in_main)
                self.video_frames_layout.addWidget(picture)

    @staticmethod
    def get_in_main(message):
        print(message, "Dabar esu Main viduj!:)")


class LabelClickBorder(QLabel):
    pictureClicked = pyqtSignal(str)  # Can be other types (list, dict, object etc.)

    def __init__(self, image, *__args):
        super().__init__(*__args)
        self.setPixmap(image)
        self.highlighted = False

    def mousePressEvent(self, event):
        self.highlighted = not self.highlighted
        if self.highlighted:
            self.setStyleSheet("border: 4px solid black")
        else:
            self.setStyleSheet("border: 0px")

        self.pictureClicked.emit("Mane spustelėjo!")


def extract_images(pathIn):
    images = []
    count = 0
    vidcap = VideoCapture(pathIn)
    success = True
    while success:
        vidcap.set(CAP_PROP_POS_MSEC, count * 1000)
        success, image = vidcap.read()
        if image is None:
            return images
        images.append(to_q_image(image))
        count = count + 1
    return images


def to_q_image(cv_img):
    height, width, channel = cv_img.shape
    bytes_per_line = 3 * width
    q_img = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
    return q_img


if __name__ == '__main__':
    appctxt = AppContext()                      # 4. Instantiate the subclass
    exit_code = appctxt.run()                   # 5. Invoke run()
    sys.exit(exit_code)
