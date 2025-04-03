import numpy as np
from PyQt6.QtGui import QImage

def image_to_array(image: QImage) -> np.ndarray:
    width, height = image.width(), image.height()
    ptr = image.bits()
    ptr.setsize(image.bytesPerLine() * height)
    
    if image.format() in [QImage.Format.Format_RGBA8888, QImage.Format.Format_ARGB32]:
        arr = np.array(ptr).reshape(height, width, 4)
        return arr[:, :, 2]
    elif image.format() == QImage.Format.Format_Grayscale8:
        arr = np.array(ptr).reshape(height, width)
        return arr
    else:
        converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
        ptr = converted.bits()
        ptr.setsize(converted.bytesPerLine() * converted.height())
        arr = np.array(ptr).reshape(converted.height(), converted.width(), 4)
        return arr[:, :, 2]

def chi_square_analysis(image: QImage, block_size: int = 16) -> np.ndarray:
    arr = image_to_array(image)
    h, w = arr.shape
    rows, cols = h // block_size, w // block_size
    chi_values = np.zeros((rows, cols))
    for i in range(rows):
        for j in range(cols):
            block = arr[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]
            observed, _ = np.histogram(block, bins=256, range=(0, 256))
            expected = np.full(observed.shape, block.size / 256)
            chi_values[i, j] = np.sum((observed - expected) ** 2 / expected)
    return chi_values
