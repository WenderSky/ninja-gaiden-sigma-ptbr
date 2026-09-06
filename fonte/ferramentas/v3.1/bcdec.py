# -*- coding: utf-8 -*-
"""Decodificador BC1 (DXT1) e BC3 (DXT5) em numpy, para renderizar as texturas
comprimidas do databin (formatos 0x59 e 0x5B do G1T). Devolve RGBA8 (h, w, 4)."""
import numpy as np


def _rgb565(c):
    r = ((c >> 11) & 31) * 255 // 31
    g = ((c >> 5) & 63) * 255 // 63
    b = (c & 31) * 255 // 31
    return np.stack([r, g, b], axis=-1).astype(np.int32)


def _bc1_color(blk, alpha_from_bc1=True):
    # blk: (n, 8) uint8
    c0 = blk[:, 0].astype(np.uint16) | (blk[:, 1].astype(np.uint16) << 8)
    c1 = blk[:, 2].astype(np.uint16) | (blk[:, 3].astype(np.uint16) << 8)
    idx = blk[:, 4].astype(np.uint32) | (blk[:, 5].astype(np.uint32) << 8) | \
          (blk[:, 6].astype(np.uint32) << 16) | (blk[:, 7].astype(np.uint32) << 24)
    p0 = _rgb565(c0); p1 = _rgb565(c1)
    four = (c0 > c1) | (not alpha_from_bc1)
    p2 = np.where(four[:, None], (2 * p0 + p1) // 3, (p0 + p1) // 2)
    p3 = np.where(four[:, None], (p0 + 2 * p1) // 3, 0)
    pal = np.stack([p0, p1, p2, p3], axis=1)  # (n,4,3)
    a3 = np.where(four, 255, 0)
    alpha = np.stack([np.full_like(a3, 255)] * 3 + [a3], axis=1)  # (n,4)
    sel = np.stack([(idx >> (2 * k)) & 3 for k in range(16)], axis=1)  # (n,16)
    rgb = np.take_along_axis(pal, sel[:, :, None], axis=1)  # (n,16,3)
    a = np.take_along_axis(alpha, sel, axis=1)  # (n,16)
    return rgb, a


def _bc3_alpha(blk):
    a0 = blk[:, 0].astype(np.int32); a1 = blk[:, 1].astype(np.int32)
    bits = np.zeros(blk.shape[0], dtype=np.uint64)
    for k in range(6):
        bits |= blk[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    pal = np.zeros((blk.shape[0], 8), dtype=np.int32)
    pal[:, 0] = a0; pal[:, 1] = a1
    gt = a0 > a1
    for k in range(1, 7):
        pal[:, k + 1] = np.where(gt, ((7 - k) * a0 + k * a1) // 7,
                                 np.where(k <= 4, ((5 - k) * a0 + k * a1) // 5, np.where(k == 5, 0, 255)))
    sel = np.stack([((bits >> np.uint64(3 * k)) & np.uint64(7)).astype(np.int64) for k in range(16)], axis=1)
    return np.take_along_axis(pal, sel, axis=1)


def decode(data, w, h, fmt):
    bw, bh = max(1, w // 4), max(1, h // 4)
    n = bw * bh
    if fmt in (0x59, 0x60, 0x06):
        blk = np.frombuffer(data[:n * 8], dtype=np.uint8).reshape(n, 8)
        rgb, a = _bc1_color(blk)
    elif fmt in (0x5B, 0x62, 0x08):
        blk = np.frombuffer(data[:n * 16], dtype=np.uint8).reshape(n, 16)
        rgb, _ = _bc1_color(blk[:, 8:], alpha_from_bc1=False)
        a = _bc3_alpha(blk[:, :8])
    else:
        raise ValueError("formato nao suportado: %#x" % fmt)
    px = np.concatenate([rgb, a[:, :, None]], axis=2).astype(np.uint8)  # (n,16,4)
    px = px.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return px[:h, :w]
