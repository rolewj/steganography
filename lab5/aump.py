import numpy as np
from PyQt6.QtGui import QImage, QColor

def aump_analysis(image: QImage, m: int = 8, d: int = 1) -> float:
    arr = np.zeros((image.height(), image.width()), dtype=np.float64)
    for y in range(image.height()):
        for x in range(image.width()):
            arr[y, x] = QColor(image.pixel(x, y)).red()
    X = arr.copy()
    Xpred, w = pred_aump(X, m, d)
    r = X - Xpred
    Xbar = X + 1 - 2 * (X.astype(int) % 2)
    beta = np.sum(w * (X - Xbar) * r)
    return beta

def pred_aump(X: np.ndarray, m: int, d: int) -> tuple:
    sig_th = 1.0
    q = d + 1
    h, w_img = X.shape
    Kn = (h * w_img) // m
    H = np.zeros((m, q))
    x_vals = np.linspace(1/m, 1, m)
    for i in range(q):
        H[:, i] = x_vals ** i
    Y = np.zeros((m, Kn))
    count = 0
    for i in range(h):
        for j in range(w_img):
            block_idx = count // m
            row_in_block = count % m
            Y[row_in_block, block_idx] = X[i, j]
            count += 1
    p = np.linalg.lstsq(H, Y, rcond=None)[0]
    Ypred = H @ p
    Xpred = np.zeros_like(X)
    count = 0
    for i in range(h):
        for j in range(w_img):
            block_idx = count // m
            row_in_block = count % m
            Xpred[i, j] = Ypred[row_in_block, block_idx]
            count += 1
    sig2 = np.sum((Y - Ypred) ** 2, axis=0) / (m - q)
    sig2 = np.maximum(sig_th ** 2, sig2)
    s_n2 = Kn / np.sum(1.0 / sig2)
    w_block = np.sqrt(s_n2 / (Kn * (m - q))) / sig2
    w_full = np.zeros_like(X)
    count = 0
    for i in range(h):
        for j in range(w_img):
            block_idx = count // m
            w_full[i, j] = w_block[block_idx]
            count += 1
    return Xpred, w_full
