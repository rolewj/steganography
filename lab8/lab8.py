import sys, re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QTextEdit
)

END_MARKER = '11111111'
RUN_RE     = re.compile(r' +')

class SteganographyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Текстовая стеганография")
        self.setGeometry(100, 100, 900, 650)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top = QHBoxLayout()
        self.load_btn = QPushButton("Загрузить файл")
        self.save_btn = QPushButton("Сохранить результат")
        self.load_btn.clicked.connect(self.load_file)
        self.save_btn.clicked.connect(self.save_file)
        top.addWidget(self.load_btn);  top.addWidget(self.save_btn)
        main_layout.addLayout(top)

        mid = QHBoxLayout()
        src_box = QVBoxLayout();  src_box.addWidget(QLabel("Исходный текст:"))
        self.source_text = QTextEdit();  src_box.addWidget(self.source_text)
        mid.addLayout(src_box)

        secret_box = QVBoxLayout();  secret_box.addWidget(QLabel("Секретное сообщение:"))
        self.secret_message = QTextEdit();  secret_box.addWidget(self.secret_message)
        mid.addLayout(secret_box)
        main_layout.addLayout(mid)

        bottom = QHBoxLayout()
        self.embed_btn = QPushButton("Встроить сообщение")
        self.extract_btn = QPushButton("Извлечь сообщение")
        self.embed_btn.clicked.connect(self.embed_message)
        self.extract_btn.clicked.connect(self.extract_message)
        bottom.addWidget(self.embed_btn);  bottom.addWidget(self.extract_btn)
        main_layout.addLayout(bottom)

        main_layout.addWidget(QLabel("Результат:"))
        self.result_text = QTextEdit();  self.result_text.setReadOnly(True)
        main_layout.addWidget(self.result_text)

    def load_file(self):
        path,_ = QFileDialog.getOpenFileName(self,"Открыть текстовый файл","",
                                             "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                with open(path,"r",encoding="utf-8") as f:
                    self.source_text.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self,"Ошибка",f"Не удалось открыть файл:\n{e}")

    def save_file(self):
        path,_ = QFileDialog.getSaveFileName(self,"Сохранить файл","",
                                             "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                with open(path,"w",encoding="utf-8") as f:
                    f.write(self.result_text.toPlainText())
                QMessageBox.information(self,"Успех","Файл сохранён")
            except Exception as e:
                QMessageBox.critical(self,"Ошибка",f"Не удалось сохранить файл:\n{e}")

    def embed_message(self):
        cover = self.source_text.toPlainText()
        secret = self.secret_message.toPlainText()
        if not cover or not secret:
            QMessageBox.warning(self,"Предупреждение",
                                "Заполните и покровный текст, и секретное сообщение")
            return

        bitstream = ''.join(f"{ord(c):08b}" for c in secret) + END_MARKER
        runs = list(RUN_RE.finditer(cover))
        if len(bitstream) > len(runs):
            QMessageBox.critical(self,"Ошибка",
                f"Недостаточно пробельных блоков.\n"
                f"Нужно {len(bitstream)}, имеется {len(runs)}")
            return

        out, last = [], 0
        for idx, m in enumerate(runs):
            out.append(cover[last:m.start()])
            block = m.group()
            if idx < len(bitstream):
                need_even = bitstream[idx] == '1'
                is_even   = len(block) % 2 == 0
                if need_even ^ is_even:
                    block += ' '
            out.append(block)
            last = m.end()
        out.append(cover[last:])

        stego = ''.join(out)
        self.result_text.setPlainText(stego)
        QMessageBox.information(self,"Успех","Секрет встроен")

    def extract_message(self):
        stego = self.source_text.toPlainText()
        if not stego:
            QMessageBox.warning(self,"Предупреждение","Нет текста для анализа")
            return

        bits = []
        for m in RUN_RE.finditer(stego):
            bits.append('1' if len(m.group()) % 2 == 0 else '0')
            if ''.join(bits[-8:]) == END_MARKER:
                break
        else:
            QMessageBox.warning(self,"Предупреждение","Маркер конца не найден")
            return

        bitstr = ''.join(bits[:-8])
        chars = [ chr(int(bitstr[i:i+8],2))
                  for i in range(0,len(bitstr),8) if len(bitstr[i:i+8])==8 ]
        secret = ''.join(chars)

        self.result_text.setPlainText(secret)
        self.secret_message.setPlainText(secret)
        QMessageBox.information(self,"Успех","Сообщение извлечено")

def main():
    app = QApplication(sys.argv)
    w = SteganographyApp();  w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
