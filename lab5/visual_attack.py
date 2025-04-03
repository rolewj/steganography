from PyQt6.QtGui import QImage, QColor

def create_bit_image(image: QImage, bit: int) -> QImage:
    if image.isNull():
        return QImage()
    width, height = image.width(), image.height()
    result = QImage(width, height, QImage.Format.Format_Grayscale8)
    for y in range(height):
        for x in range(width):
            color = QColor(image.pixel(x, y))
            gray_val = color.red()
            extracted_bit = (gray_val >> bit) & 1
            result.setPixel(x, y, 0xFFFFFF if extracted_bit else 0)
    return result
