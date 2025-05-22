import sys, os
import difflib, math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QTabWidget,
    QPlainTextEdit, QGroupBox, QDialog, QDialogButtonBox
)
from PyQt6.QtGui import QPixmap, QImage, QColor
from PyQt6.QtCore import Qt

def text_to_bits(text: str) -> list[int]:
    data = text.encode('utf-8', errors='replace')
    bits = []
    for byte in data:
        for i in range(8):
            bit = (byte >> (7 - i)) & 1
            bits.append(bit)
    return bits

def bits_to_text(bits: list[int]) -> str:
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
    text = raw_bytes.decode('utf-8', errors='replace')
    return text

def embed_imnp(cover: QImage, bits: list[int]):
    if cover.isNull():
        return QImage(), QImage(), []
    cover_gray = cover.convertToFormat(QImage.Format.Format_Grayscale8)
    width = cover_gray.width()
    height = cover_gray.height()
    stego = cover_gray.copy()
    inter = cover_gray.copy()
    embedded_positions = []
    bit_index = 0
    for y in range(0, height-2, 2):
        for x in range(0, width-2, 2):
            corners = [cover_gray.pixelColor(x, y).red(), cover_gray.pixelColor(x+2, y).red(), cover_gray.pixelColor(x, y+2).red(), cover_gray.pixelColor(x+2, y+2).red()]
            Omin = min(corners)
            Omax = max(corners)
            C00 = cover_gray.pixelColor(x, y).red()
            C01 = (Omax + ((cover_gray.pixelColor(x, y).red() + cover_gray.pixelColor(x, y+2).red()) // 2)) // 2
            C10 = (Omax + ((cover_gray.pixelColor(x, y).red() + cover_gray.pixelColor(x+2, y).red()) // 2)) // 2
            C11 = (C01 + C10) // 2
            C = [[C00, C01], [C10, C11]]
            vk1 = C[0][1] - Omin
            vk2 = C[1][0] - Omin
            vk3 = C[1][1] - Omin
            for idx, (dx, dy) in enumerate([(0,1), (1,0), (1,1)]):
                vk = vk1 if idx == 0 else vk2 if idx == 1 else vk3
                ak = math.floor(math.log2(vk)) if vk > 0 else 0
                if ak > 0 and bit_index + ak <= len(bits):
                    if (dx, dy) == (1,1):
                        ref = min(C[1][0], C[0][1])
                    elif (dx, dy) == (0,1):
                        ref = max(cover_gray.pixelColor(x, y).red(), cover_gray.pixelColor(x, y+2).red())
                    else:
                        ref = max(cover_gray.pixelColor(x, y).red(), cover_gray.pixelColor(x+2, y).red())
                    Rk = 0
                    for b in bits[bit_index:bit_index+ak]:
                        Rk = (Rk << 1) | b
                    bit_index += ak
                    new_val = ref - Rk
                    if new_val < 0:
                        new_val = 0
                    if new_val > 255:
                        new_val = 255
                    stego.setPixelColor(x+dx, y+dy, QColor(new_val, new_val, new_val))
                    embedded_positions.append((x+dx, y+dy))
                else:
                    stego.setPixelColor(x+dx, y+dy, QColor(C[dx][dy], C[dx][dy], C[dx][dy]))
                inter.setPixelColor(x+dx, y+dy, QColor(C[dx][dy], C[dx][dy], C[dx][dy]))
    return stego, inter, embedded_positions

def extract_imnp(stego: QImage, msg_length: int):
    if stego.isNull():
        return []
    cover_gray = stego.convertToFormat(QImage.Format.Format_Grayscale8)
    width = cover_gray.width()
    height = cover_gray.height()
    total_bits = msg_length * 8
    bits = []
    extracted = 0
    for y in range(0, height-2, 2):
        for x in range(0, width-2, 2):
            corners = [cover_gray.pixelColor(x, y).red(), cover_gray.pixelColor(x+2, y).red(), cover_gray.pixelColor(x, y+2).red(), cover_gray.pixelColor(x+2, y+2).red()]
            Omin = min(corners)
            Omax = max(corners)
            C00 = cover_gray.pixelColor(x, y).red()
            C01 = (Omax + ((cover_gray.pixelColor(x, y).red() + cover_gray.pixelColor(x, y+2).red()) // 2)) // 2
            C10 = (Omax + ((cover_gray.pixelColor(x, y).red() + cover_gray.pixelColor(x+2, y).red()) // 2)) // 2
            C11 = (C01 + C10) // 2
            C = [[C00, C01], [C10, C11]]
            vk1 = C[0][1] - Omin
            vk2 = C[1][0] - Omin
            vk3 = C[1][1] - Omin
            for idx, (dx, dy) in enumerate([(0,1), (1,0), (1,1)]):
                if extracted >= total_bits:
                    break
                vk = vk1 if idx == 0 else vk2 if idx == 1 else vk3
                ak = math.floor(math.log2(vk)) if vk > 0 else 0
                if ak > 0 and extracted + ak <= total_bits:
                    if (dx, dy) == (1,1):
                        ref = min(C[1][0], C[0][1])
                    elif (dx, dy) == (0,1):
                        ref = max(cover_gray.pixelColor(x, y).red(), cover_gray.pixelColor(x, y+2).red())
                    else:
                        ref = max(cover_gray.pixelColor(x, y).red(), cover_gray.pixelColor(x+2, y).red())
                    Rk = ref - cover_gray.pixelColor(x+dx, y+dy).red()
                    if Rk < 0:
                        Rk = 0
                    for pos in range(ak-1, -1, -1):
                        bit = (Rk >> pos) & 1
                        bits.append(bit)
                    extracted += ak
    return bits[:total_bits]

def compute_capacity(cover: QImage):
    gray = cover.convertToFormat(QImage.Format.Format_Grayscale8)
    w, h = gray.width(), gray.height()
    total_bits = 0
    for y in range(0, h-2, 2):
        for x in range(0, w-2, 2):
            # читаем четыре угловых пикселя
            p00 = gray.pixelColor(x,   y).red()
            p01 = gray.pixelColor(x+2, y).red()
            p10 = gray.pixelColor(x,   y+2).red()
            p11 = gray.pixelColor(x+2, y+2).red()
            Omin = min(p00, p01, p10, p11)
            # вычисляем vk для трёх встраиваемых позиций
            vk1 = ((Omin := Omin) or 1) and (( (Omax:=max(p00,p01,p10,p11)) + ((p00 + p10)//2) )//2 - Omin)
            vk2 = (Omax + ((p00 + p01)//2))//2 - Omin
            vk3 = (( (Omax) + ((p01 + p10)//2) )//2) - Omin
            for vk in (vk1, vk2, vk3):
                if vk > 1:
                    total_bits += math.floor(math.log2(vk))
    return total_bits, total_bits // 8


def compute_psnr(cover: QImage, stego: QImage):
    cover_gray = cover.convertToFormat(QImage.Format.Format_Grayscale8)
    stego_gray = stego.convertToFormat(QImage.Format.Format_Grayscale8)
    width, height = cover_gray.width(), cover_gray.height()
    mse = 0
    for y in range(height):
        for x in range(width):
            diff = cover_gray.pixelColor(x, y).red() - stego_gray.pixelColor(x, y).red()
            mse += diff * diff
    mse /= (width * height)
    if mse == 0:
        return float('inf')
    return 10 * math.log10((255 ** 2) / mse)

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

class IMNP(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMNP")
        self.resize(1200, 600)
        self.original_image = QImage()
        self.processed_image = QImage()
        self.interpolated_image = QImage()
        self.used_indices = []
        self.last_embedded_text = ""
        self.last_saved_filepath = ""
        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.init_embed_tab()
        self.init_extract_tab()
        self.init_batch_tab()

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

    def init_batch_tab(self):
        self.tab_batch = QWidget()
        self.tabs.addTab(self.tab_batch, "Задание 4")
        layout = QVBoxLayout(self.tab_batch)
        hl = QHBoxLayout()
        btn_in = QPushButton("Входная папка")
        btn_in.clicked.connect(self.select_input_folder)
        self.lbl_input = QLabel("Не выбрано")
        hl.addWidget(btn_in)
        hl.addWidget(self.lbl_input)
        layout.addLayout(hl)
        hl2 = QHBoxLayout()
        btn_out = QPushButton("Выходная папка")
        btn_out.clicked.connect(self.select_output_folder)
        self.lbl_output = QLabel("Не выбрано")
        hl2.addWidget(btn_out)
        hl2.addWidget(self.lbl_output)
        layout.addLayout(hl2)
        self.txt_percents = QPlainTextEdit()
        self.txt_percents.setPlaceholderText("10,50,100")
        layout.addWidget(self.txt_percents)
        btn_run = QPushButton("Старт")
        btn_run.clicked.connect(self.run_batch_embedding)
        layout.addWidget(btn_run)

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
        bits = text_to_bits(message_text)
        result_image, inter_img, used_idx = embed_imnp(self.original_image, bits)
        if result_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Недостаточно пикселей для встраивания!")
            return
        self.processed_image = result_image
        self.interpolated_image = inter_img
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
        width = self.original_image.convertToFormat(QImage.Format.Format_Grayscale8).width()
        height = self.original_image.convertToFormat(QImage.Format.Format_Grayscale8).height()
        diff_sum = 0
        for y in range(height):
            for x in range(width):
                diff_sum += abs(self.original_image.convertToFormat(QImage.Format.Format_Grayscale8).pixelColor(x, y).red() - self.processed_image.convertToFormat(QImage.Format.Format_Grayscale8).pixelColor(x, y).red())
        avg_diff = diff_sum / (width * height) if (width * height) else 0
        perc_all = (avg_diff / 255) * 100
        self.lbl_diff_all.setText(f"Изменение по всем пикселям: {perc_all:.4f}%")
        bits_count = len(bits)
        bytes_count = bits_count // 8
        chars_count = len(message_text)
        self.lbl_embed_info.setText(
            f"Встроено: {bits_count} бит ({bytes_count} байт), {chars_count} символов"
        )
        QMessageBox.information(self, "OK", "Сообщение встроено (IMNP).")

    def save_watermarked_image(self):
        if self.processed_image.isNull():
            QMessageBox.warning(self, "Ошибка", "Нет результата!")
            return
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not folder:
            return 
        base_name = os.path.splitext(os.path.basename(self.lbl_original_path.text()))[0]
        filename = f"{base_name}_IMNP.bmp"
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
        raw_bits = extract_imnp(self.processed_image, len(self.last_embedded_text))
        extracted_text = bits_to_text(raw_bits)
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
        cap_bits, cap_bytes = compute_capacity(self.interpolated_image)
        psnr_val = compute_psnr(self.interpolated_image, self.processed_image)
        diff_img = create_diff_image(self.interpolated_image, self.processed_image)

        dialog = QDialog(self)
        dialog.setWindowTitle("Визуальный анализ стегоконтейнера")
        layout = QVBoxLayout(dialog)

        info_label = QLabel(f"Ёмкость: {cap_bits} бит ({cap_bytes} байт)\nPSNR: {psnr_val:.2f} dB")
        layout.addWidget(info_label)

        h_layout = QHBoxLayout()

        v_layout_orig = QVBoxLayout()
        label_orig_title = QLabel("Исходное")
        label_orig_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout_orig.addWidget(label_orig_title)
        lbl_orig = QLabel()
        pix_orig = QPixmap.fromImage(self.interpolated_image).scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
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

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите входную папку")
        if folder:
            self.input_dir = folder
            self.lbl_input.setText(folder)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите выходную папку")
        if folder:
            self.output_dir = folder
            self.lbl_output.setText(folder)

    def run_batch_embedding(self):
        if not hasattr(self, 'input_dir') or not hasattr(self, 'output_dir') or not self.txt_percents.toPlainText():
            QMessageBox.warning(self, "Ошибка", "Укажите все параметры")
            return
        percents = [int(p) for p in self.txt_percents.toPlainText().split(',') if p.strip().isdigit()]
        os.makedirs(self.output_dir, exist_ok=True)
        for fn in os.listdir(self.input_dir):
            path = os.path.join(self.input_dir, fn)
            img = QImage(path)
            if img.isNull(): continue
            cap_bits, _ = compute_capacity(img)
            base, ext = os.path.splitext(fn)
            fmt = ext.lstrip('.').upper()
            for p in percents:
                n = cap_bits * p // 100
                bits = [0] * n
                result_image, inter_img, used_idx = embed_imnp(img, bits)
                out = os.path.join(self.output_dir, f"{base}_lab4_stego_{p}.{fmt}")
                result_image.save(out, fmt)
        QMessageBox.information(self, "OK", "Генерация завершена")

            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IMNP()
    window.show()
    sys.exit(app.exec())
