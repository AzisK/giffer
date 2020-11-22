import io
import sys

from PIL import Image
from PyQt5.QtCore import pyqtSignal, QBuffer, Qt
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QMovie
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QShortcut, QHBoxLayout, QPushButton, QVBoxLayout, \
    QWidget, QFileDialog, QScrollArea
from cv2 import CAP_PROP_POS_MSEC, VideoCapture
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
        self.selected_images = []
        # self.showMaximized()

    def init_ui(self):
        self.add_shortcuts()

        widget = QWidget()
        vLayout = QVBoxLayout()

        self.main_view = self.add_corgo()
        vLayout.addWidget(self.main_view)

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

        self.btn_add = QPushButton("Generate GIF")
        self.btn_add.clicked.connect(self.generate_gif)
        vLayout.addWidget(self.btn_add)

        scroll = self.add_video_frames_area()
        vLayout.addWidget(scroll)

        widget.setLayout(vLayout)
        self.setCentralWidget(widget)

    def add_video_frames_area(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(1)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        scroll.setFixedHeight(140)
        scroll.setWidget(content)
        self.video_frames_layout = QHBoxLayout(content)
        return scroll

    def add_corgo(self):
        label = QLabel()
        pixmap = QPixmap.fromImage(self.ctx.img_corgo)
        label.setPixmap(pixmap)
        label.setScaledContents(True)

        return label

    def add_shortcuts(self):
        self.quit_sc = QShortcut(QKeySequence('Ctrl+W'), self)
        self.quit_sc.activated.connect(QApplication.instance().quit)

        self.copy_frame = QShortcut(QKeySequence('Ctrl+C'), self)
        self.copy_frame.activated.connect(self.copy_last_highlighted)

    def get_files(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setNameFilters(["Source files (*.mov *.mp4)"])

        if dlg.exec_():
            file_name = dlg.selectedFiles()[0]
            images = extract_images(file_name)
            for image in images:
                pixmap = QPixmap.fromImage(image)
                picture = LabelClickBorder(pixmap, self)
                picture.pictureClicked.connect(self.get_in_main)
                self.video_frames_layout.addWidget(picture)

    def generate_gif(self):
        fp = "gifs/image.gif"

        # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif
        img, *imgs = [qpixmap_to_pil(i) for i in self.selected_images]

        img.save(fp=fp, format='GIF', append_images=imgs, save_all=True, duration=320, loop=0)
        gif = QMovie(fp)
        self.main_view.setMovie(gif)
        gif.start()

    @staticmethod
    def get_in_main(message):
        print(message, "Dabar esu Main viduj!:)")

    def copy_last_highlighted(self):
        last = self.selected_images[-1]
        widget = LabelClickBorder(last, self)
        self.video_frames_layout.addWidget(widget)
        print(self.video_frames_layout.count())


class LabelClickBorder(QLabel):
    pictureClicked = pyqtSignal(str)  # Can be other types (list, dict, object etc.)
    STYLE = "border: 2px solid rgba(0, 0, 0, 0);"
    STYLE_HIGHLIGHTED = "border: 2px solid black;"

    def __init__(self, pixmap, main_window, *__args):
        super().__init__(*__args)
        self.main_window = main_window
        self.pixmap = pixmap.scaledToHeight(256)
        self.setPixmap(self.pixmap.scaledToHeight(100))
        self.highlighted = False
        self.setStyleSheet(self.STYLE)

    def mousePressEvent(self, event):
        self.highlighted = not self.highlighted
        if self.highlighted:
            self.setStyleSheet(self.STYLE_HIGHLIGHTED)
            self.main_window.selected_images.append(self.pixmap)
        else:
            self.setStyleSheet(self.STYLE)

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
        images.append(cv_image_to_qimage(image))
        count = count + 1
    return images


def cv_image_to_qimage(cv_img):
    height, width, channel = cv_img.shape
    bytes_per_line = 3 * width
    q_img = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
    return q_img


def qpixmap_to_pil(qpixmap):
    buffer = QBuffer()
    buffer.open(QBuffer.ReadWrite)
    qpixmap.save(buffer, "PNG")
    pil_im = Image.open(io.BytesIO(buffer.data()))
    return pil_im


if __name__ == '__main__':
    appctxt = AppContext()                      # 4. Instantiate the subclass
    exit_code = appctxt.run()                   # 5. Invoke run()
    sys.exit(exit_code)
