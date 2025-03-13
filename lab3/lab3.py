import sys, os
import difflib, math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QTabWidget,
    QPlainTextEdit, QGroupBox, QDialog, QDialogButtonBox
)
from PyQt6.QtGui import QPixmap, QImage, QColor
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

def f(yi, yi_plus):
    return ((yi // 2) + yi_plus) & 1

def adjust_first_pixel(pixel, constant, target_m):
    candidate_minus = pixel - 1 if pixel > 0 else None
    candidate_plus  = pixel + 1 if pixel < 255 else None
    if candidate_minus is not None and f(candidate_minus, constant) == target_m:
        return candidate_minus
    if candidate_plus is not None and f(candidate_plus, constant) == target_m:
        return candidate_plus
    return candidate_plus if candidate_plus is not None else candidate_minus if candidate_minus is not None else pixel

def adjust_second_pixel(pixel, constant, target_m):
    candidate_minus = pixel - 1 if pixel > 0 else None
    candidate_plus  = pixel + 1 if pixel < 255 else None
    if pixel % 2 == 0:
        if candidate_plus is not None and f(constant, candidate_plus) == target_m:
            return candidate_plus
        if candidate_minus is not None and f(constant, candidate_minus) == target_m:
            return candidate_minus
    else:
        if candidate_minus is not None and f(constant, candidate_minus) == target_m:
            return candidate_minus
        if candidate_plus is not None and f(constant, candidate_plus) == target_m:
            return candidate_plus
    return candidate_plus if candidate_plus is not None else candidate_minus if candidate_minus is not None else pixel

def embed_lsb_matching_revisited(cover: QImage, bits: list[int]):
    if cover.isNull():
        return QImage(), []
    cover_gray = cover.convertToFormat(QImage.Format.Format_Grayscale8)
    width, height = cover_gray.width(), cover_gray.height()
    total_pixels = width * height
    if total_pixels % 2 == 1:
        total_pixels -= 1
    total_pairs = total_pixels // 2
    if len(bits) > total_pairs * 2:
        return QImage(), []
    result = QImage(cover_gray)
    bit_index = 0
    for i in range(total_pairs):
        idx1 = 2 * i
        idx2 = 2 * i + 1
        y1, x1 = idx1 // width, idx1 % width
        y2, x2 = idx2 // width, idx2 % width
        pixel1 = result.pixelColor(x1, y1).red()
        pixel2 = result.pixelColor(x2, y2).red()
        m1 = bits[bit_index] if bit_index < len(bits) else 0
        bit_index += 1
        m2 = bits[bit_index] if bit_index < len(bits) else 0
        bit_index += 1
        if (pixel1 & 1) != m1:
            new_pixel1 = adjust_first_pixel(pixel1, pixel2, m2)
            new_pixel2 = pixel2
        else:
            new_pixel1 = pixel1
            if f(new_pixel1, pixel2) == m2:
                new_pixel2 = pixel2
            else:
                new_pixel2 = adjust_second_pixel(pixel2, new_pixel1, m2)  
        result.setPixelColor(x1, y1, QColor(new_pixel1, new_pixel1, new_pixel1))
        result.setPixelColor(x2, y2, QColor(new_pixel2, new_pixel2, new_pixel2))
    used_indices = list(range(total_pixels))
    return result, used_indices

def extract_lsb_matching_revisited(stego: QImage):
    if stego.isNull():
        return []
    stego_gray = stego.convertToFormat(QImage.Format.Format_Grayscale8)
    width, height = stego_gray.width(), stego_gray.height()
    total_pixels = width * height
    if total_pixels % 2 == 1:
        total_pixels -= 1
    total_pairs = total_pixels // 2
    extracted_bits = []
    for i in range(total_pairs):
        idx1 = 2 * i
        idx2 = 2 * i + 1
        y1, x1 = idx1 // width, idx1 % width
        y2, x2 = idx2 // width, idx2 % width
        pixel1 = stego_gray.pixelColor(x1, y1).red()
        pixel2 = stego_gray.pixelColor(x2, y2).red()
        extracted_bits.append(pixel1 & 1)
        extracted_bits.append(f(pixel1, pixel2))
    return extracted_bits

def compute_capacity(cover: QImage):
    width, height = cover.width(), cover.height()
    total_pixels = width * height
    if total_pixels % 2 == 1:
        total_pixels -= 1
    capacity_bits = total_pixels
    capacity_bytes = capacity_bits // 8
    return capacity_bits, capacity_bytes

def compute_psnr(cover: QImage, stego: QImage):
    cover_gray = cover.convertToFormat(QImage.Format.Format_Grayscale8)
    stego_gray = stego.convertToFormat(QImage.Format.Format_Grayscale8)
    width, height = cover_gray.width(), cover_gray.height()
    mse = 0
    count = width * height
    for y in range(height):
        for x in range(width):
            diff = cover_gray.pixelColor(x, y).red() - stego_gray.pixelColor(x, y).red()
            mse += diff * diff
    mse /= count
    if mse == 0:
        return float('inf')
    psnr = 10 * math.log10((255 ** 2) / mse)
    return psnr

def create_diff_image(cover: QImage, stego: QImage):
    cover_gray = cover.convertToFormat(QImage.Format.Format_Grayscale8)
    stego_gray = stego.convertToFormat(QImage.Format.Format_Grayscale8)
    width, height = cover_gray.width(), cover_gray.height()
    diff_img = QImage(width, height, QImage.Format.Format_Grayscale8)
    for y in range(height):
        for x in range(width):
            diff = abs(cover_gray.pixelColor(x, y).red() - stego_gray.pixelColor(x, y).red())
            diff_img.setPixelColor(x, y, QColor(diff, diff, diff))
    return diff_img

class LSBMR(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LSB Matching Revisited")
        self.resize(1200, 600)
        self.original_image = QImage()
        self.processed_image = QImage()
        self.used_indices = []
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

        self.btn_embed = QPushButton("Встроить")
        self.btn_embed.clicked.connect(self.embed_message)
        control_layout.addWidget(self.btn_embed)

        self.btn_save = QPushButton("Сохранить результат")
        self.btn_save.clicked.connect(self.save_watermarked_image)
        control_layout.addWidget(self.btn_save)

        self.btn_analyze = QPushButton("Визуальный анализ")
        self.btn_analyze.clicked.connect(self.visual_analysis)
        control_layout.addWidget(self.btn_analyze)

        self.lbl_embed_info = QLabel("Встроено: -")
        control_layout.addWidget(self.lbl_embed_info)

        self.lbl_diff_all = QLabel("Изменение по всем пикселям: -")
        control_layout.addWidget(self.lbl_diff_all)

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

        self.btn_select_embedded = QPushButton("Загрузить стегоконтейнер")
        self.btn_select_embedded.clicked.connect(self.select_embedded_image)
        control_layout.addWidget(self.btn_select_embedded)

        self.lbl_embedded_path = QLabel("Файл не выбран")
        control_layout.addWidget(self.lbl_embedded_path)

        self.btn_extract = QPushButton("Извлечь")
        self.btn_extract.clicked.connect(self.extract_message)
        control_layout.addWidget(self.btn_extract)

        self.txt_extracted = QPlainTextEdit()
        self.txt_extracted.setReadOnly(True)
        self.txt_extracted.setPlaceholderText("Извлечённый текст...")
        control_layout.addWidget(self.txt_extracted)

        self.btn_measure_error = QPushButton("Измерить ошибку (%)")
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
        bits = text_to_bits_with_marker(message_text)
        result_image, used_idx = embed_lsb_matching_revisited(self.original_image, bits)
        if result_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Недостаточно пикселей для встраивания!")
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
        cover_gray = self.original_image.convertToFormat(QImage.Format.Format_Grayscale8)
        stego_gray = self.processed_image.convertToFormat(QImage.Format.Format_Grayscale8)
        width, height = cover_gray.width(), cover_gray.height()
        diff_sum = 0
        count = width * height
        for y in range(height):
            for x in range(width):
                diff_sum += abs(cover_gray.pixelColor(x, y).red() - stego_gray.pixelColor(x, y).red())
        avg_diff = diff_sum / count if count else 0
        perc_all = (avg_diff / 255) * 100
        self.lbl_diff_all.setText(f"Изменение по всем пикселям: {perc_all:.4f}%")
        bits_count = len(bits)
        bytes_count = bits_count // 8
        chars_count = len(message_text)
        self.lbl_embed_info.setText(
            f"Встроено: {bits_count} бит ({bytes_count} байт), {chars_count} символов"
        )
        QMessageBox.information(self, "OK", "Сообщение встроено (LSBMR).")

    def save_watermarked_image(self):
        if self.processed_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Нет результата!")
            return
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not folder:
            return 
        base_name = os.path.splitext(os.path.basename(self.lbl_original_path.text()))[0]
        filename = f"{base_name}_LSBMR_exact.bmp"
        save_path = os.path.join(folder, filename).replace("\\", "/")
        if self.processed_image.save(save_path, "BMP"):
            self.last_saved_filepath = save_path
            QMessageBox.information(self, "OK", f"Файл сохранен: {save_path}")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить файл!")

    def select_embedded_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить стегоконтейнер",
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
        raw_bits = extract_lsb_matching_revisited(self.processed_image)
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
        QMessageBox.information(self, "Результат", f"Ошибка в извлечении: {error_percent:.2f}%")

    def visual_analysis(self):
        if self.original_image.isNull() or self.processed_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Необходимо загрузить оригинальное и стего-изображение!")
            return
        cap_bits, cap_bytes = compute_capacity(self.original_image)
        psnr_val = compute_psnr(self.original_image, self.processed_image)
        diff_img = create_diff_image(self.original_image, self.processed_image)

        dialog = QDialog(self)
        dialog.setWindowTitle("Визуальный анализ стегоконтейнера")
        layout = QVBoxLayout(dialog)

        info_label = QLabel(f"Ёмкость: {cap_bits} бит ({cap_bytes} байт)\nPSNR: {psnr_val:.2f} dB")
        layout.addWidget(info_label)

        h_layout = QHBoxLayout()

        v_layout_orig = QVBoxLayout()
        label_orig_title = QLabel("Оригинальное")
        label_orig_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout_orig.addWidget(label_orig_title)
        lbl_orig = QLabel()
        pix_orig = QPixmap.fromImage(self.original_image).scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
        lbl_orig.setPixmap(pix_orig)
        lbl_orig.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout_orig.addWidget(lbl_orig)
        h_layout.addLayout(v_layout_orig)

        v_layout_stego = QVBoxLayout()
        label_stego_title = QLabel("Стего-изображение")
        label_stego_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout_stego.addWidget(label_stego_title)
        lbl_stego = QLabel()
        pix_stego = QPixmap.fromImage(self.processed_image).scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
        lbl_stego.setPixmap(pix_stego)
        lbl_stego.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout_stego.addWidget(lbl_stego)
        h_layout.addLayout(v_layout_stego)

        v_layout_diff = QVBoxLayout()
        label_diff_title = QLabel("Разница")
        label_diff_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout_diff.addWidget(label_diff_title)
        lbl_diff = QLabel()
        pix_diff = QPixmap.fromImage(diff_img).scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
        lbl_diff.setPixmap(pix_diff)
        lbl_diff.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout_diff.addWidget(lbl_diff)
        h_layout.addLayout(v_layout_diff)

        layout.addLayout(h_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        close_button.setText("Закрыть")
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LSBMR()
    window.show()
    sys.exit(app.exec())
