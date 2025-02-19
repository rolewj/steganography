import sys, os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QRadioButton,
    QGroupBox, QSplitter
)
from PyQt6.QtGui import QPixmap, QImage, QColor
from PyQt6.QtCore import Qt

def create_bit_image(image, bit):
    if image.isNull():
        return QImage()
    width, height = image.width(), image.height()
    result = QImage(width, height, QImage.Format.Format_Grayscale8)
    for y in range(height):
        for x in range(width):
            color = QColor(image.pixel(x, y))
            gray_val = color.red()
            extracted_bit = (gray_val >> bit) & 1
            result.setPixel(x, y, 0xffffff if extracted_bit else 0)
    return result

class BitImageVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Битовая визуализация")
        self.resize(1000, 500)
        self.selected_bit = 0
        self.image_path = None
        self.original_image = QImage()
        self.processed_image = QImage()
        central_area = QWidget()
        self.setCentralWidget(central_area)
        main_layout = QHBoxLayout(central_area)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        self.init_controls(splitter)
        self.init_image_view(splitter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def init_controls(self, parent):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.btn_select_image = QPushButton("Выбрать картинку")
        self.btn_select_image.clicked.connect(self.select_image)
        layout.addWidget(self.btn_select_image)
        self.lbl_file = QLabel("Нет файла")
        layout.addWidget(self.lbl_file)
        group_bits = QGroupBox("Выбор бита")
        bits_layout = QHBoxLayout(group_bits)
        self.radio_buttons = []
        for i in range(8):
            rb = QRadioButton(str(i))
            rb.clicked.connect(self.on_bit_selected)
            self.radio_buttons.append(rb)
            bits_layout.addWidget(rb)
        self.radio_buttons[0].setChecked(True)
        layout.addWidget(group_bits)
        self.btn_show_bit = QPushButton("Показать выбранный бит")
        self.btn_show_bit.clicked.connect(self.show_bit)
        layout.addWidget(self.btn_show_bit)
        self.btn_save_single = QPushButton("Сохранить один бит")
        self.btn_save_single.clicked.connect(self.save_one_bit)
        layout.addWidget(self.btn_save_single)
        self.btn_save_all = QPushButton("Сохранить все биты")
        self.btn_save_all.clicked.connect(self.save_all_bits)
        layout.addWidget(self.btn_save_all)
        layout.addStretch(1)
        parent.addWidget(panel)

    def init_image_view(self, parent):
        view_widget = QWidget()
        layout_view = QHBoxLayout(view_widget)
        group_original = QGroupBox("Исходное")
        layout_original = QVBoxLayout(group_original)
        self.lbl_original = QLabel("Нет картинки")
        self.lbl_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_original.setFixedSize(400, 400)
        layout_original.addWidget(self.lbl_original)
        layout_view.addWidget(group_original)
        group_processed = QGroupBox("Результат")
        layout_processed = QVBoxLayout(group_processed)
        self.lbl_processed = QLabel("Нет картинки")
        self.lbl_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_processed.setFixedSize(400, 400)
        layout_processed.addWidget(self.lbl_processed)
        layout_view.addWidget(group_processed)
        parent.addWidget(view_widget)

    def on_bit_selected(self):
        for i, rb in enumerate(self.radio_buttons):
            if rb.isChecked():
                self.selected_bit = i
                break

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите картинку",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.pgm);;Все файлы (*)"
        )
        if file_path:
            self.image_path = file_path
            self.lbl_file.setText(file_path)
            if not self.original_image.load(file_path):
                QMessageBox.warning(self, "Ошибка", "Не удалось открыть!")
                return
            if self.original_image.format() != QImage.Format.Format_Grayscale8:
                self.original_image = self.original_image.convertToFormat(QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(self.original_image).scaled(
                self.lbl_original.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_original.setPixmap(pixmap)

    def show_bit(self):
        if self.original_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Сначала выберите картинку!")
            return
        self.processed_image = create_bit_image(self.original_image, self.selected_bit)
        pixmap = QPixmap.fromImage(self.processed_image).scaled(
            self.lbl_processed.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_processed.setPixmap(pixmap)

    def save_one_bit(self):
        if self.processed_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Нет результата!")
            return
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not folder:
            return
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        save_name = f"{base_name}_bit_{self.selected_bit}.bmp"
        save_path = os.path.join(folder, save_name)
        save_path = save_path.replace("\\", "/")
        if self.processed_image.save(save_path, "BMP"):
            QMessageBox.information(self, "Успех", f"Один бит сохранен: {save_path}")
        else:
            QMessageBox.warning(self, "Ошибка", "Не вышло сохранить!")

    def save_all_bits(self):
        if self.original_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Сначала выберите картинку!")
            return
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not folder:
            return
        success = True
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        save_path = ""  
        for b in range(8):
            bit_image = create_bit_image(self.original_image, b)
            save_name = f"{base_name}_bit_{b}.bmp"
            path_tmp = os.path.join(folder, save_name)
            path_tmp = path_tmp.replace("\\", "/")
            if not bit_image.save(path_tmp, "BMP"):
                success = False
            save_path = path_tmp
        QMessageBox.information(
            self,
            "Успех",
            f"Все биты сохранены: {save_path}" if success else "Ошибка при сохранении одного или нескольких файлов"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BitImageVisualizer()
    window.show()
    sys.exit(app.exec())
