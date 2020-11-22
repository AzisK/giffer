import io
import sys
from shutil import copyfile

from PIL import Image
from PyQt5.QtCore import pyqtSignal, QBuffer, Qt
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QMovie, QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QShortcut, QHBoxLayout, QPushButton, QVBoxLayout, \
    QWidget, QFileDialog, QScrollArea, QAction, QToolBar
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

    @cached_property
    def save_png(self):
        return self.get_resource('images/Save.png')

    @cached_property
    def working_gif(self):
        return self.get_resource('work/working_gif.gif')


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super(MainWindow, self).__init__()
        self.ctx = ctx  # Store a reference to the context for resources, etc.
        self.title = "Giffer"
        self.setWindowTitle(self.title)

        self.init_ui()
        self.selected_images = []
        # self.showMaximized()

    def file_save(self):
        name = QFileDialog.getSaveFileName(self, 'Save File')[0]
        if name:
            name = name + '.gif' if not name.endswith('.gif') else name
            copyfile(self.ctx.working_gif, name)

    def init_ui(self):
        self.add_shortcuts()

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget()
        widget.setLayout(vLayout)

        vLayout.addWidget(self.add_toolbar())

        self.main_view = self.add_corgo()
        vLayout.addWidget(self.main_view)

        buttons_layout1 = QHBoxLayout()
        self.btn_generate = QPushButton("Generate GIF")
        self.btn_generate.clicked.connect(self.generate_gif)
        buttons_layout1.addWidget(self.btn_generate)
        self.btn_remove = QPushButton("Remove Unselected")
        self.btn_remove.clicked.connect(self.remove_unselected)
        buttons_layout1.addWidget(self.btn_remove)
        vLayout.addLayout(buttons_layout1)

        vLayout.addWidget(self.add_selected_frames_area())
        self.select_frames_layout.addWidget(self.add_corgo_frame())

        buttons_layout2 = QHBoxLayout()
        self.btn = QPushButton("Select Source")
        self.btn.clicked.connect(self.get_files)
        buttons_layout2.addWidget(self.btn)
        self.btn_add = QPushButton("Add Frames")
        self.btn_add.clicked.connect(self.add_frames)
        buttons_layout2.addWidget(self.btn_add)
        vLayout.addLayout(buttons_layout2)

        vLayout.addWidget(self.add_video_frames_area())

        self.setCentralWidget(widget)

    def add_toolbar(self):
        toolBar = QToolBar()
        save_file_action = QAction(QIcon(self.ctx.save_png), "Save", self)
        save_file_action.setStatusTip("Save GIF")
        save_file_action.triggered.connect(self.file_save)
        toolBar.addAction(save_file_action)
        return toolBar

    def add_video_frames_area(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(1)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        scroll.setFixedHeight(140)
        scroll.setWidget(content)
        self.video_frames_layout = QHBoxLayout(content)
        return scroll

    def add_selected_frames_area(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(1)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        scroll.setFixedHeight(260)
        scroll.setWidget(content)
        self.select_frames_layout = QHBoxLayout(content)
        return scroll

    def add_corgo(self):
        label = QLabel()
        pixmap = QPixmap.fromImage(self.ctx.img_corgo)
        label.setPixmap(pixmap)
        label.setScaledContents(True)

        return label

    def add_corgo_frame(self, height=256):
        pixmap = QPixmap.fromImage(self.ctx.img_corgo)
        return LabelSelected(pixmap, self, height)

    def add_shortcuts(self):
        self.quit_sc = QShortcut(QKeySequence('Ctrl+W'), self)
        self.quit_sc.activated.connect(QApplication.instance().quit)

        self.copy_frame = QShortcut(QKeySequence('Ctrl+C'), self)
        self.copy_frame.activated.connect(self.copy_highlighted)

    def get_files(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setNameFilters(["Source files (*.mov *.mp4)"])

        if dlg.exec_():
            file_name = dlg.selectedFiles()[0]
            images = extract_images(file_name)
            for image in images:
                pixmap = QPixmap.fromImage(image)
                picture = LabelVideoFrame(pixmap, self)
                picture.pictureClicked.connect(self.get_in_main)
                self.video_frames_layout.addWidget(picture)

    def add_frames(self):
        widgets = [LabelSelected(i.original_pixmap, self, 256) for i in self.layout_children(self.video_frames_layout) if i.highlighted]
        for w in widgets:
            self.select_frames_layout.addWidget(w)

    def generate_gif(self):
        fp = self.ctx.working_gif

        # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif
        img, *imgs = [qpixmap_to_pil(i.original_pixmap) for i in self.layout_children(self.select_frames_layout) if i.highlighted]

        img.save(fp=fp, format='GIF', append_images=imgs, save_all=True, duration=320, loop=0)
        gif = QMovie(fp)
        self.main_view.setMovie(gif)
        gif.start()

    def copy_highlighted(self):
        widgets = [LabelVideoFrame(i.original_pixmap, self) for i in self.layout_children(self.video_frames_layout) if i.highlighted]
        for w in widgets:
            self.video_frames_layout.addWidget(w)

    def remove_unselected(self):
        widgets = [i for i in self.layout_children(self.select_frames_layout) if not i.highlighted]
        for w in widgets:
            w.deleteLater()

    @staticmethod
    def get_in_main(message):
        print(message, "Dabar esu Main viduj!:)")

    @staticmethod
    def layout_children(layout):
        cnt = layout.count()
        return [layout.itemAt(i).widget() for i in range(cnt)]


class LabelVideoFrame(QLabel):
    pictureClicked = pyqtSignal(str)  # Can be other types (list, dict, object etc.)
    STYLE = "border: 2px solid rgba(0, 0, 0, 0);"
    STYLE_HIGHLIGHTED = "border: 2px solid black;"
    INITIAL_STATE = False

    @property
    def initial_style(self):
        return self.STYLE

    def __init__(self, pixmap, main_window, height=100, *__args):
        super().__init__(*__args)
        self.main_window = main_window
        self.original_pixmap = pixmap.scaledToHeight(256)
        self.setPixmap(self.original_pixmap.scaledToHeight(height))
        self.highlighted = self.INITIAL_STATE
        self.setStyleSheet(self.initial_style)

    def mousePressEvent(self, event):
        self.highlighted = not self.highlighted
        if self.highlighted:
            self.setStyleSheet(self.STYLE_HIGHLIGHTED)
            # self.main_window.selected_images.append(self.original_pixmap)
        else:
            self.setStyleSheet(self.STYLE)

        self.pictureClicked.emit("Mane spustelėjo!")


class LabelSelected(LabelVideoFrame):
    INITIAL_STATE = True

    @property
    def initial_style(self):
        return self.STYLE_HIGHLIGHTED


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
    q_img = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
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
