import numpy as np
from PyQt6.QtGui import QImage
import math

def get_red(pixel: int) -> int:
    return (pixel >> 16) & 0xff

def get_green(pixel: int) -> int:
    return (pixel >> 8) & 0xff

def get_blue(pixel: int) -> int:
    return pixel & 0xff

def get_pixel_colour(pixel: int, colour: int) -> int:
    return get_red(pixel)

def negate_lsb(byte: int) -> int:
    temp = byte & 0xFE
    if temp == byte:
        return byte | 0x01
    else:
        return temp

def invert_lsb(byte: int) -> int:
    if byte == 255:
        return 256
    if byte == 256:
        return 255
    return negate_lsb(byte + 1) - 1

def invert_mask(mask: list[int]) -> list[int]:
    return [-m for m in mask]

def flip_block(block: list[int], mask: list[int]) -> list[int]:
    new_block = []
    for i, pixel in enumerate(block):
        val = get_pixel_colour(pixel, 0)
        if mask[i] == 1:
            val = negate_lsb(val)
        elif mask[i] == -1:
            val = invert_lsb(val)
        new_pixel = (0xff << 24) | (val << 16) | (val << 8) | val
        new_block.append(new_pixel)
    return new_block

def get_variation(block: list[int], colour: int) -> float:
    var = 0
    for i in range(0, len(block), 4):
        if i + 3 < len(block):
            c0 = get_pixel_colour(block[i], colour)
            c1 = get_pixel_colour(block[i+1], colour)
            c2 = get_pixel_colour(block[i+2], colour)
            c3 = get_pixel_colour(block[i+3], colour)
            var += abs(c0 - c1)
            var += abs(c3 - c2)
            var += abs(c1 - c3)
            var += abs(c2 - c0)
    return var

def get_negative_variation(block: list[int], colour: int, mask: list[int]) -> float:
    var = 0
    for i in range(0, len(block), 4):
        if i + 3 < len(block):
            c0 = get_pixel_colour(block[i], colour)
            c1 = get_pixel_colour(block[i+1], colour)
            c2 = get_pixel_colour(block[i+2], colour)
            c3 = get_pixel_colour(block[i+3], colour)
            if mask[i] == -1:
                c0 = invert_lsb(c0)
            if mask[i+1] == -1:
                c1 = invert_lsb(c1)
            if mask[i+2] == -1:
                c2 = invert_lsb(c2)
            if mask[i+3] == -1:
                c3 = invert_lsb(c3)
            var += abs(c0 - c1)
            var += abs(c3 - c2)
            var += abs(c1 - c3)
            var += abs(c2 - c0)
    return var

def getX(r, rm, r1, rm1, s, sm, s1, sm1):
    dzero = r - s        
    dminuszero = rm - sm  
    done = r1 - s1       
    dminusone = rm1 - sm1 
    a = 2 * (done + dzero)
    b = dminuszero - dminusone - done - (3 * dzero)
    c = dzero - dminuszero
    if a == 0:
        x = c / b
    else:
        discriminant = b**2 - 4 * a * c
        if discriminant >= 0:
            rootpos = ((-b) + math.sqrt(discriminant)) / (2 * a)
            rootneg = ((-b) - math.sqrt(discriminant)) / (2 * a)
            x = rootpos if abs(rootpos) <= abs(rootneg) else rootneg
        else:
            cr = (rm - r) / (r1 - r + rm - rm1) if (r1 - r + rm - rm1)!=0 else 0
            cs = (sm - s) / (s1 - s + sm - sm1) if (s1 - s + sm - sm1)!=0 else 0
            x = (cr + cs) / 2
    if x == 0:
        cr = (rm - r) / (r1 - r + rm - rm1) if (r1 - r + rm - rm1)!=0 else 0
        cs = (sm - s) / (s1 - s + sm - sm1) if (s1 - s + sm - sm1)!=0 else 0
        x = (cr + cs) / 2
    return x

def create_masks_static(m: int, n: int) -> tuple[list[int], list[int]]:
    mask_pos = []
    mask_neg = []
    for i in range(n):
        for j in range(m):
            if ((j % 2 == 0 and i % 2 == 0) or (j % 2 == 1 and i % 2 == 1)):
                mask_pos.append(1)
                mask_neg.append(0)
            else:
                mask_pos.append(0)
                mask_neg.append(1)
    return mask_pos, mask_neg

def get_all_pixel_flips(image: QImage, colour: int, overlap: bool, m: int, n: int) -> list[float]:
    imgx = image.width()
    imgy = image.height()
    allmask = [1] * (m * n)
    startx = 0
    starty = 0
    block_size = m * n
    numregular = 0.0
    numsingular = 0.0
    numnegreg = 0.0
    numnegsing = 0.0

    while startx < imgx and starty < imgy:
        for _ in range(2):
            block = []
            for i in range(n):
                for j in range(m):
                    x = startx + j
                    y = starty + i
                    if x < imgx and y < imgy:
                        pixel = image.pixel(x, y)
                        block.append(pixel)
            if len(block) < block_size:
                continue
            block_flipped = flip_block(block.copy(), allmask)
            variationB = get_variation(block_flipped, colour)
            mask_pos, mask_neg = create_masks_static(m, n)
            current_mask = mask_pos
            block_flipped_mask = flip_block(block.copy(), current_mask)
            variationP = get_variation(block_flipped_mask, colour)
            neg_mask = invert_mask(current_mask)
            variationN = get_negative_variation(block, colour, neg_mask)
            if variationP > variationB:
                numregular += 1
            elif variationP < variationB:
                numsingular += 1
            if variationN > variationB:
                numnegreg += 1
            elif variationN < variationB:
                numnegsing += 1
        if overlap:
            startx += 1
        else:
            startx += m
        if startx >= (imgx - 1):
            startx = 0
            if overlap:
                starty += 1
            else:
                starty += n
        if starty >= (imgy - 1):
            break
    return [numregular, numsingular, numnegreg, numnegsing]

class RSAnalysis:
    ANALYSIS_COLOUR_RED = 0
    ANALYSIS_COLOUR_GREEN = 1
    ANALYSIS_COLOUR_BLUE = 2

    def __init__(self, m: int, n: int):
        self.mM = m
        self.mN = n
        self.mMask = self.create_masks(m, n)

    def create_masks(self, m: int, n: int) -> list[list[int]]:
        mask_pos = []
        mask_neg = []
        for i in range(n):
            for j in range(m):
                if ((j % 2 == 0 and i % 2 == 0) or (j % 2 == 1 and i % 2 == 1)):
                    mask_pos.append(1)
                    mask_neg.append(0)
                else:
                    mask_pos.append(0)
                    mask_neg.append(1)
        return [mask_pos, mask_neg]

    def do_analysis(self, image: QImage, colour: int, overlap: bool) -> np.ndarray:
        imgx = image.width()
        imgy = image.height()
        startx = 0
        starty = 0
        block_size = self.mM * self.mN
        numregular = 0.0
        numsingular = 0.0
        numnegreg = 0.0
        numnegsing = 0.0
        numunusable = 0.0

        while startx < imgx and starty < imgy:
            for m in range(2):
                block = []
                for i in range(self.mN):
                    for j in range(self.mM):
                        x = startx + j
                        y = starty + i
                        if x < imgx and y < imgy:
                            pixel = image.pixel(x, y)
                            block.append(pixel)
                if len(block) < block_size:
                    continue
                variationB = get_variation(block, colour)
                block_flipped = flip_block(block.copy(), self.mMask[m])
                variationP = get_variation(block_flipped, colour)
                block_restored = flip_block(block_flipped.copy(), self.mMask[m])
                neg_mask = invert_mask(self.mMask[m])
                variationN = get_negative_variation(block_restored, colour, neg_mask)
                if variationP > variationB:
                    numregular += 1
                elif variationP < variationB:
                    numsingular += 1
                else:
                    numunusable += 1
                if variationN > variationB:
                    numnegreg += 1
                elif variationN < variationB:
                    numnegsing += 1
            if overlap:
                startx += 1
            else:
                startx += self.mM
            if startx >= (imgx - 1):
                startx = 0
                if overlap:
                    starty += 1
                else:
                    starty += self.mN
            if starty >= (imgy - 1):
                break

        total_groups = numregular + numsingular + numunusable + 1e-6
        rs_ratio = numregular / total_groups

        allpixels = get_all_pixel_flips(image, colour, overlap, self.mM, self.mN)
        x = getX(numregular, numnegreg, allpixels[0], allpixels[2],
                 numsingular, numnegsing, allpixels[1], allpixels[3])
        if (2 * (x - 1)) == 0:
            epf = 0
        else:
            epf = abs(x / (2 * (x - 1)))
        if (x - 0.5) == 0:
            ml = 0
        else:
            ml = abs(x / (x - 0.5))
        results = np.zeros(28)
        results[0] = numregular
        results[1] = numsingular
        results[2] = numnegreg
        results[3] = numnegsing
        results[4] = abs(numregular - numnegreg)
        results[5] = abs(numsingular - numnegsing)
        results[6] = (numregular / total_groups) * 100
        results[7] = (numsingular / total_groups) * 100
        results[8] = (numnegreg / total_groups) * 100
        results[9] = (numnegsing / total_groups) * 100
        results[10] = (results[4] / total_groups) * 100
        results[11] = (results[5] / total_groups) * 100
        results[12] = allpixels[0]
        results[13] = allpixels[1]
        results[14] = allpixels[2]
        results[15] = allpixels[3]
        results[16] = abs(allpixels[0] - allpixels[1])
        results[17] = abs(allpixels[2] - allpixels[3])
        results[18] = (allpixels[0] / total_groups) * 100
        results[19] = (allpixels[1] / total_groups) * 100
        results[20] = (allpixels[2] / total_groups) * 100
        results[21] = (allpixels[3] / total_groups) * 100
        results[22] = (results[16] / total_groups) * 100
        results[23] = (results[17] / total_groups) * 100
        results[24] = total_groups
        results[25] = epf
        results[26] = ml
        results[27] = ((imgx * imgy) * ml) / 8
        return results

    def get_result_names(self) -> list[str]:
        names = [
            "Number of regular groups (positive)",
            "Number of singular groups (positive)",
            "Number of regular groups (negative)",
            "Number of singular groups (negative)",
            "Difference for regular groups",
            "Difference for singular groups",
            "Percentage of regular groups (positive)",
            "Percentage of singular groups (positive)",
            "Percentage of regular groups (negative)",
            "Percentage of singular groups (negative)",
            "Difference for regular groups %",
            "Difference for singular groups %",
            "Number of regular groups (positive for all flipped)",
            "Number of singular groups (positive for all flipped)",
            "Number of regular groups (negative for all flipped)",
            "Number of singular groups (negative for all flipped)",
            "Difference for regular groups (all flipped)",
            "Difference for singular groups (all flipped)",
            "Percentage of regular groups (positive for all flipped)",
            "Percentage of singular groups (positive for all flipped)",
            "Percentage of regular groups (negative for all flipped)",
            "Percentage of singular groups (negative for all flipped)",
            "Difference for regular groups (all flipped) %",
            "Difference for singular groups (all flipped) %",
            "Total number of groups",
            "Estimated percent of flipped pixels",
            "Estimated message length (in percent of pixels)(p)",
            "Estimated message length (in bytes)"
        ]
        return names

def rs_analysis(image: QImage, colour: int = RSAnalysis.ANALYSIS_COLOUR_RED, overlap: bool = False) -> np.ndarray:
    analyzer = RSAnalysis(2, 2)
    return analyzer.do_analysis(image, colour, overlap)