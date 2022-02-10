import io
import sys
from shutil import copyfile

from PIL import Image
from PyQt5.QtCore import pyqtSignal, QBuffer, Qt
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QMovie, QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QShortcut, QHBoxLayout, QPushButton, QVBoxLayout, \
    QWidget, QFileDialog, QScrollArea, QAction, QToolBar, QSlider
from cv2 import CAP_PROP_POS_MSEC, VideoCapture
from fbs_runtime.application_context.PyQt5 import ApplicationContext, cached_property

DEFAULT_GIF_HEIGHT = 384
DEFAULT_VIDEO_READ_INTERVAL = 500


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
        self.showMaximized()

    def file_save(self):
        name = QFileDialog.getSaveFileName(self, 'Save File')[0]
        if name:
            name = name + '.gif' if not name.endswith('.gif') else name
            copyfile(self.ctx.working_gif, name)

    def init_ui(self):
        self.add_shortcuts()

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(1)
        widget = QWidget()
        scroll.setWidget(widget)

        widget.setLayout(vLayout)

        vLayout.addWidget(self.add_toolbar())

        self.gif_view = self.setup_gif_view()
        self.add_corgo()
        vLayout.addWidget(self.gif_view)

        vLayout.addLayout(self.add_gif_buttons())

        vLayout.addWidget(self.add_selected_frames_area())

        vLayout.addLayout(self.add_frame_buttons())

        vLayout.addWidget(self.add_video_frames_area())

        self.setCentralWidget(scroll)

    def add_toolbar(self):
        toolbar = QToolBar()
        save_file_action = QAction(QIcon(self.ctx.save_png), "Save", self)
        save_file_action.setStatusTip("Save GIF")
        save_file_action.triggered.connect(self.file_save)
        toolbar.addAction(save_file_action)
        return toolbar

    def add_gif_buttons(self):
        layout = QHBoxLayout()

        self.btn_stop = form_button('Generate GIF', self.generate_gif, layout)

        self.btn_stop = form_button('Stop', self.stop, layout)

        self.btn_remove = form_button('Remove Unselected', self.remove_unselected, layout)

        self.height = form_slider(
            text='Height', function=self.update_height, layout=layout,
            range1=128, range2=1024, default=DEFAULT_GIF_HEIGHT
        )

        self.delay = form_slider(
            text='Delay', function=self.update_delay, layout=layout,
            range1=100, range2=1000, default=200
        )

        return layout

    def update_height(self, value):
        self.height.setText(f'{value}')
        self.generate_gif()

    def update_delay(self, value):
        self.delay.setText(f'{value}')
        self.generate_gif()

    def add_frame_buttons(self):
        layout = QHBoxLayout()

        self.btn = form_button('Select Source', self.get_files, layout)

        self.btn_add = form_button('Add Frames', self.add_frames, layout)

        self.read = form_slider(
            text='Read', function=self.update_read, layout=layout,
            range1=100, range2=2000, default=DEFAULT_VIDEO_READ_INTERVAL
        )

        return layout

    def update_read(self, value):
        self.read.setText(f'{value}')

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
        scroll.setFixedHeight(198)
        scroll.setWidget(content)
        self.select_frames_layout = QHBoxLayout(content)
        self.select_frames_layout.setContentsMargins(0, 0, 0, 0)
        self.select_frames_layout.setAlignment(Qt.AlignLeft)
        return scroll

    def setup_gif_view(self):
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        return label

    def adjust_corgo(self):
        pixmap = QPixmap.fromImage(self.ctx.img_corgo)
        height = int(self.height.text())
        self.gif_view.setPixmap(pixmap.scaledToHeight(height))

    def add_corgo(self):
        pixmap = QPixmap.fromImage(self.ctx.img_corgo)
        self.gif_view.setPixmap(pixmap.scaledToHeight(DEFAULT_GIF_HEIGHT))

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
            images = self.extract_images(file_name)
            for image in images:
                pixmap = QPixmap.fromImage(image)
                picture = LabelVideoFrame(pixmap, self)
                picture.pictureClicked.connect(self.get_in_main)
                self.video_frames_layout.addWidget(picture)

    def add_frames(self):
        widgets = [LabelSelected(i.original_pixmap, self, 192) for i in self.layout_children(self.video_frames_layout) if i.highlighted]
        for w in widgets:
            self.select_frames_layout.addWidget(w)

    def stop(self):
        self.gif_view.movie().stop()

    def generate_gif(self):
        # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif
        select_frames_labels = self.layout_children(self.select_frames_layout)
        if not select_frames_labels:
            self.adjust_corgo()
            return
        pixmaps = [i.original_pixmap for i in select_frames_labels if i.highlighted]
        height = int(self.height.text())
        img, *imgs = [qpixmap_to_pil(i.scaledToHeight(height)) for i in pixmaps]

        fp = self.ctx.working_gif
        delay = int(self.delay.text())
        img.save(fp=fp, format='GIF', append_images=imgs, save_all=True, duration=delay, loop=0)
        gif = QMovie(fp)
        self.gif_view.setMovie(gif)
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

    def extract_images(self, pathIn):
        images = []
        count = 0
        vidcap = VideoCapture(pathIn)
        success = True
        while success:
            vidcap.set(CAP_PROP_POS_MSEC, count * int(self.read.text()))
            success, image = vidcap.read()
            if image is None:
                return images
            images.append(cv_image_to_qimage(image))
            count = count + 1
        return images


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
        self.original_pixmap = pixmap
        self.setPixmap(self.original_pixmap.scaledToHeight(height))
        self.highlighted = self.INITIAL_STATE
        self.setStyleSheet(self.initial_style)

    def mousePressEvent(self, event):
        self.highlighted = not self.highlighted
        if self.highlighted:
            self.setStyleSheet(self.STYLE_HIGHLIGHTED)
        else:
            self.setStyleSheet(self.STYLE)

        self.pictureClicked.emit("Mane spustelėjo!")


class LabelSelected(LabelVideoFrame):
    INITIAL_STATE = True

    @property
    def initial_style(self):
        return self.STYLE_HIGHLIGHTED


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


def form_button(text, function, layout):
    btn = QPushButton(text)
    btn.clicked.connect(function)
    layout.addWidget(btn)
    return btn


def form_slider(text, function, layout, range1, range2, default):
    height = QLabel(text)
    height.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    height.setMaximumWidth(60)
    layout.addWidget(height)

    sld = QSlider(Qt.Horizontal)
    sld.setRange(range1, range2)
    sld.setValue(DEFAULT_GIF_HEIGHT)
    sld.setMaximumWidth(160)
    sld.valueChanged.connect(function)
    layout.addWidget(sld)

    value = QLabel(str(default))
    value.setAlignment(Qt.AlignCenter)
    value.setMaximumWidth(80)
    layout.addWidget(value)
    return value


if __name__ == '__main__':
    appctxt = AppContext()                      # 4. Instantiate the subclass
    exit_code = appctxt.run()                   # 5. Invoke run()
    sys.exit(exit_code)
