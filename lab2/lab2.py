import sys, os
import numpy as np
import difflib
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QTabWidget,
    QPlainTextEdit, QDoubleSpinBox, QLineEdit, QGroupBox
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt

END_MARKER = b"\xfe\x00\xff\xfa"

def text_to_bits_with_marker(text: str) -> list[int]:
    data = text.encode('utf-8', errors='replace')
    data_marker = data + END_MARKER
    bits = []
    for byte in data_marker:
        for i in range(8):
            bit = (byte >> (7 - i)) & 1
            bits.append(bit)
    return bits

def bits_to_text_with_marker(bits: list[int]) -> str:
    if not bits:
        return ""
    r = len(bits) % 8
    if r != 0:
        bits += [0] * (8 - r)
    raw_bytes = bytearray()
    for i in range(0, len(bits), 8):
        val = 0
        for b in bits[i:i+8]:
            val = (val << 1) | b
        raw_bytes.append(val)
    idx_marker = raw_bytes.find(END_MARKER)
    if idx_marker < 0:
        payload = raw_bytes
    else:
        payload = raw_bytes[:idx_marker]
    text = payload.decode('utf-8', errors='replace')
    return text

def brightness(r, g, b):
    return 0.299 * r + 0.587 * g + 0.114 * b

def embed_kjb(cover: QImage, bits: list[int], lam: float, seed: int):
    if cover.isNull():
        return QImage(), []
    width, height = cover.width(), cover.height()
    total_pixels = width * height
    if len(bits) > total_pixels:
        return QImage(), []
    cover = cover.convertToFormat(QImage.Format.Format_RGB888)
    result = QImage(cover)
    rng = np.random.default_rng(seed)
    all_indices = np.arange(total_pixels)
    rng.shuffle(all_indices)
    used_indices = all_indices[:len(bits)]
    for i, bit_val in enumerate(bits):
        linear_index = used_indices[i]
        y = linear_index // width
        x = linear_index % width
        color = result.pixelColor(x, y)
        R, G, B_val = color.red(), color.green(), color.blue()
        Y = brightness(R, G, B_val)
        if bit_val == 1:
            B_new = B_val + lam * Y
        else:
            B_new = B_val - lam * Y
        B_new = max(0, min(255, B_new))
        color.setBlue(int(B_new))
        result.setPixelColor(x, y, color)
    return result, used_indices

def extract_kjb(image: QImage, lam: float, seed: int) -> list[int]:
    if image.isNull():
        return []
    width, height = image.width(), image.height()
    total_pixels = width * height
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    rng = np.random.default_rng(seed)
    all_indices = np.arange(total_pixels)
    rng.shuffle(all_indices)
    bits = []
    for i in range(total_pixels):
        linear_index = all_indices[i]
        y = linear_index // width
        x = linear_index % width
        color = image.pixelColor(x, y)
        B_val = color.blue()
        neighbors = []
        if x > 0:
            neighbors.append(image.pixelColor(x - 1, y).blue())
        if x < width - 1:
            neighbors.append(image.pixelColor(x + 1, y).blue())
        if y > 0:
            neighbors.append(image.pixelColor(x, y - 1).blue())
        if y < height - 1:
            neighbors.append(image.pixelColor(x, y + 1).blue())
        b_est = sum(neighbors) / len(neighbors) if neighbors else B_val
        bit = 1 if B_val >= b_est else 0
        bits.append(bit)
    return bits

def measure_blue_diff(original: QImage, watermarked: QImage) -> float:
    if original.isNull() or watermarked.isNull():
        return 0.0
    width, height = original.width(), original.height()
    if width != watermarked.width() or height != watermarked.height():
        return 0.0
    orig = original.convertToFormat(QImage.Format.Format_RGB888)
    watermarked = watermarked.convertToFormat(QImage.Format.Format_RGB888)
    total_pixels = width * height
    diff_sum = 0
    for y in range(height):
        for x in range(width):
            diff_sum += abs(orig.pixelColor(x, y).blue() - watermarked.pixelColor(x, y).blue())
    return diff_sum / total_pixels

def measure_changed_only(original: QImage, watermarked: QImage, used_indices: np.ndarray) -> float:
    if original.isNull() or watermarked.isNull() or used_indices.size == 0:
        return 0.0
    width, height = original.width(), original.height()
    if width != watermarked.width() or height != watermarked.height():
        return 0.0
    orig = original.convertToFormat(QImage.Format.Format_RGB888)
    watermarked = watermarked.convertToFormat(QImage.Format.Format_RGB888)
    diff_sum = 0
    for linear_index in used_indices:
        y = linear_index // width
        x = linear_index % width
        diff_sum += abs(orig.pixelColor(x, y).blue() - watermarked.pixelColor(x, y).blue())
    return diff_sum / used_indices.size

class KJBVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Метод Куттера-Джордана-Боссена")
        self.resize(1200, 600)
        self.original_image = QImage()
        self.processed_image = QImage()
        self.used_indices = np.array([], dtype=np.int64)
        self.last_embedded_text = ""
        self.last_saved_filepath = ""
        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.init_embed_tab()
        self.init_extract_tab()

    def init_embed_tab(self):
        self.tab_embed = QWidget()
        self.tabs.addTab(self.tab_embed, "Встраивание")
        main_layout = QHBoxLayout(self.tab_embed)

        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.btn_select_cover = QPushButton("Загрузить оригинал")
        self.btn_select_cover.clicked.connect(self.select_cover_image)
        control_layout.addWidget(self.btn_select_cover)

        self.lbl_original_path = QLabel("Файл не выбран")
        control_layout.addWidget(self.lbl_original_path)

        self.txt_input = QPlainTextEdit()
        self.txt_input.setPlaceholderText("Введите сообщение")
        control_layout.addWidget(self.txt_input)

        group_lambda = QGroupBox("λ (энергия)")
        lambda_layout = QHBoxLayout(group_lambda)
        self.spin_lambda = QDoubleSpinBox()
        self.spin_lambda.setRange(0.01, 10.0)
        self.spin_lambda.setSingleStep(0.01)
        self.spin_lambda.setValue(0.1)
        lambda_layout.addWidget(self.spin_lambda)
        control_layout.addWidget(group_lambda)

        group_seed = QGroupBox("Seed")
        seed_layout = QHBoxLayout(group_seed)
        self.seed_line = QLineEdit("12345")
        seed_layout.addWidget(self.seed_line)
        control_layout.addWidget(group_seed)

        self.btn_embed = QPushButton("Встроить")
        self.btn_embed.clicked.connect(self.embed_message)
        control_layout.addWidget(self.btn_embed)

        self.btn_save = QPushButton("Сохранить результат")
        self.btn_save.clicked.connect(self.save_watermarked_image)
        control_layout.addWidget(self.btn_save)

        self.lbl_diff_all = QLabel("Изменение по всем пикселям: -")
        control_layout.addWidget(self.lbl_diff_all)

        self.lbl_diff_changed = QLabel("Изменение только в изменённых: -")
        control_layout.addWidget(self.lbl_diff_changed)

        control_layout.addStretch(1)
        main_layout.addWidget(control_panel, 0)

        image_panel = QWidget()
        image_layout = QHBoxLayout(image_panel)

        group_original = QGroupBox("Исходное")
        layout_original = QVBoxLayout(group_original)
        self.lbl_original_display = QLabel("Нет картинки")
        self.lbl_original_display.setFixedSize(400, 400)
        self.lbl_original_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_original.addWidget(self.lbl_original_display)
        image_layout.addWidget(group_original)

        group_processed = QGroupBox("Встроенное")
        layout_processed = QVBoxLayout(group_processed)
        self.lbl_processed_display = QLabel("Нет картинки")
        self.lbl_processed_display.setFixedSize(400, 400)
        self.lbl_processed_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_processed.addWidget(self.lbl_processed_display)
        image_layout.addWidget(group_processed)

        main_layout.addWidget(image_panel, 1)

    def init_extract_tab(self):
        self.tab_extract = QWidget()
        self.tabs.addTab(self.tab_extract, "Извлечение")
        main_layout = QHBoxLayout(self.tab_extract)

        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.btn_select_embedded = QPushButton("Загрузить картинку с ЦВЗ")
        self.btn_select_embedded.clicked.connect(self.select_embedded_image)
        control_layout.addWidget(self.btn_select_embedded)

        self.lbl_embedded_path = QLabel("Файл не выбран")
        control_layout.addWidget(self.lbl_embedded_path)

        group_seed_extract = QGroupBox("Seed")
        seed_layout_extract = QHBoxLayout(group_seed_extract)
        self.seed_line_extract = QLineEdit("12345")
        seed_layout_extract.addWidget(self.seed_line_extract)
        control_layout.addWidget(group_seed_extract)

        self.btn_extract = QPushButton("Извлечь")
        self.btn_extract.clicked.connect(self.extract_message)
        control_layout.addWidget(self.btn_extract)

        self.txt_extracted = QPlainTextEdit()
        self.txt_extracted.setReadOnly(True)
        self.txt_extracted.setPlaceholderText("Извлечённый текст...")
        control_layout.addWidget(self.txt_extracted)

        self.btn_measure_error = QPushButton("Измерить ошибку в процентах")
        self.btn_measure_error.clicked.connect(self.measure_extraction_error)
        control_layout.addWidget(self.btn_measure_error)

        control_layout.addStretch(1)
        main_layout.addWidget(control_panel, 0)

        image_panel = QWidget()
        image_layout = QHBoxLayout(image_panel)
        group_embedded = QGroupBox("Изображение")
        layout_embedded = QVBoxLayout(group_embedded)
        self.lbl_embedded_display = QLabel("Нет картинки")
        self.lbl_embedded_display.setFixedSize(400, 400)
        self.lbl_embedded_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_embedded.addWidget(self.lbl_embedded_display)
        image_layout.addWidget(group_embedded)
        main_layout.addWidget(image_panel, 1)

    def select_cover_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите исходное изображение",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.pgm);;Все файлы (*)"
        )
        if file_path:
            image = QImage(file_path)
            if image.isNull():
                QMessageBox.warning(self, "Ошибка", "Не удалось открыть!")
                return
            self.original_image = image
            self.lbl_original_path.setText(file_path)
            pixmap = QPixmap.fromImage(image).scaled(
                self.lbl_original_display.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_original_display.setPixmap(pixmap)

    def embed_message(self):
        if self.original_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Нет исходного изображения!")
            return
        message_text = self.txt_input.toPlainText()
        if not message_text:
            QMessageBox.warning(self, "Ошибка", "Введите текст!")
            return
        lam = self.spin_lambda.value()
        try:
            seed_value = int(self.seed_line.text())
        except ValueError:
            seed_value = 12345
        bits = text_to_bits_with_marker(message_text)
        result_image, used_idx = embed_kjb(self.original_image, bits, lam, seed_value)
        if result_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Недостаточно пикселей!")
            return
        self.processed_image = result_image
        self.used_indices = used_idx
        self.last_embedded_text = message_text
        pix_original = QPixmap.fromImage(self.original_image).scaled(
            self.lbl_original_display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_original_display.setPixmap(pix_original)
        pix_processed = QPixmap.fromImage(result_image).scaled(
            self.lbl_processed_display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_processed_display.setPixmap(pix_processed)
        diff_all = measure_blue_diff(self.original_image, self.processed_image)
        diff_changed = measure_changed_only(self.original_image, self.processed_image, used_idx)
        perc_all = (diff_all / 255) * 100
        perc_changed = (diff_changed / 255) * 100
        self.lbl_diff_all.setText(f"Изменение по всем пикселям: {perc_all:.4f}%")
        self.lbl_diff_changed.setText(f"Изменение только в изменённых: {perc_changed:.4f}%")
        QMessageBox.information(self, "OK", "Сообщение встроено.")

    def save_watermarked_image(self):
        if self.processed_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Нет результата!")
            return
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not folder:
            return
        base_name = os.path.splitext(os.path.basename(self.lbl_original_path.text()))[0]
        lam_str = f"{self.spin_lambda.value():.2f}".replace('.', '_')
        filename = f"{base_name}_Lam{lam_str}.bmp"
        save_path = os.path.join(folder, filename).replace("\\", "/")
        if self.processed_image.save(save_path, "BMP"):
            self.last_saved_filepath = save_path
            QMessageBox.information(self, "OK", f"Файл сохранен: {save_path}")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить файл!")

    def select_embedded_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите картинку с ЦВЗ",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.pgm);;Все файлы (*)"
        )
        if file_path:
            image = QImage(file_path)
            if image.isNull():
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить!")
                return
            self.processed_image = image
            self.lbl_embedded_path.setText(file_path)
            pixmap = QPixmap.fromImage(image).scaled(
                self.lbl_embedded_display.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_embedded_display.setPixmap(pixmap)

    def extract_message(self):
        if self.processed_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Нет изображения для извлечения!")
            return
        try:
            seed_value = int(self.seed_line_extract.text())
        except ValueError:
            seed_value = 12345
        raw_bits = extract_kjb(self.processed_image, 0, seed_value)
        extracted_text = bits_to_text_with_marker(raw_bits)
        self.txt_extracted.setPlainText(extracted_text)
        QMessageBox.information(self, "OK", "Сообщение извлечено.")

    def measure_extraction_error(self):
        if not self.last_saved_filepath:
            QMessageBox.warning(self, "Ошибка", "Файл с встраиванием не был сохранён!")
            return
        loaded_filename = os.path.basename(self.lbl_embedded_path.text())
        last_saved_filename = os.path.basename(self.last_saved_filepath)
        if loaded_filename != last_saved_filename:
            QMessageBox.warning(self, "Ошибка", "Загруженный файл не совпадает с последним сохранённым!")
            return
        original_text = self.last_embedded_text
        extracted_text = self.txt_extracted.toPlainText()
        if not original_text or not extracted_text:
            QMessageBox.warning(self, "Ошибка", "Отсутствует оригинальный или извлечённый текст!")
            return
        sequence_matcher = difflib.SequenceMatcher(None, original_text, extracted_text)
        ratio = sequence_matcher.ratio()
        error_percent = (1 - ratio) * 100
        QMessageBox.information(self, "Ошибка", f"Ошибка в извлечении: {error_percent:.2f}%")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KJBVisualizer()
    window.show()
    sys.exit(app.exec())
