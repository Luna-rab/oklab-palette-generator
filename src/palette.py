"""知覚的色空間（Oklab）における電荷反発モデルを用いたカラーパレット生成."""

from typing import NamedTuple

import numpy as np
from scipy.optimize import minimize

# Björn Ottosson の Oklab 変換行列 (https://bottosson.github.io/posts/oklab/)。
# _M1: linear sRGB → LMS、_M2: cbrt(LMS) → Oklab。逆変換用に転置ではなく
# 実際の逆行列 _M1_INV / _M2_INV を定数として持つ。
_M1 = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ],
    dtype=np.float64,
)

_M2 = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ],
    dtype=np.float64,
)

_M2_INV = np.array(
    [
        [1.0, 0.3963377774, 0.2158037573],
        [1.0, -0.1055613458, -0.0638541728],
        [1.0, -0.0894841775, -1.2914855480],
    ],
    dtype=np.float64,
)

_M1_INV = np.array(
    [
        [4.0767416621, -3.3077115913, 0.2309699292],
        [-1.2684380046, 2.6097574011, -0.3413193965],
        [-0.0041960863, -0.7034186147, 1.7076147010],
    ],
    dtype=np.float64,
)


def hex_to_srgb(hex_str: str) -> np.ndarray:
    h = hex_str.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {hex_str!r}")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return np.array([r, g, b], dtype=np.float64)


def srgb_to_hex(srgb: np.ndarray) -> str:
    clipped = np.clip(srgb, 0.0, 1.0)
    ints = np.round(clipped * 255.0).astype(int)
    return f"#{int(ints[0]):02x}{int(ints[1]):02x}{int(ints[2]):02x}"


def srgb_to_linear(srgb: np.ndarray) -> np.ndarray:
    threshold = 0.04045
    # np.where は両ブランチを評価するため、負値で np.power が NaN を返さない
    # ように clip してから冪計算する。threshold 分岐自体は元の値で行う。
    safe = np.maximum(srgb, 0.0)
    return np.where(
        srgb <= threshold,
        srgb / 12.92,
        ((safe + 0.055) / 1.055) ** 2.4,
    )


def linear_to_srgb(linear: np.ndarray) -> np.ndarray:
    threshold = 0.0031308
    # srgb_to_linear と同じ理由で safe 側だけ np.power に渡す。
    safe = np.maximum(linear, 0.0)
    return np.where(
        linear <= threshold,
        linear * 12.92,
        1.055 * np.power(safe, 1.0 / 2.4) - 0.055,
    )


def linear_to_oklab(linear: np.ndarray) -> np.ndarray:
    # linear RGB → LMS → cbrt(LMS) → Oklab の 3 段階。
    # np.cbrt を使うのは、ガマット外の負値 LMS でも定義される必要があるため
    # （** (1/3) は負値で NaN になる）。
    lms = linear @ _M1.T
    lms_cbrt = np.cbrt(lms)
    return lms_cbrt @ _M2.T


def oklab_to_linear(oklab: np.ndarray) -> np.ndarray:
    lms_cbrt = oklab @ _M2_INV.T
    lms = lms_cbrt**3
    return lms @ _M1_INV.T


def hex_to_oklab(hex_str: str) -> np.ndarray:
    return linear_to_oklab(srgb_to_linear(hex_to_srgb(hex_str)))


def _clip_to_gamut(points: np.ndarray, iters: int = 30, tol: float = 1e-7) -> np.ndarray:
    """(N, 3) の Oklab 点群を linear RGB ガマット内にクリップする.

    L を保ったまま (a, b) を原点方向に縮める倍率を点ごとに二分探索する。
    全点を並列に処理することで Python ループによるオーバーヘッドを回避。
    sRGB ガマットは **linear RGB 空間で立方体** になる（sRGB 空間は非線形
    なので立方体にならない）。よって判定は linear 側で行う。

    iters: 二分探索の反復回数。30 反復で ≈1e-9 精度（最終出力用）。
    最適化中の評価は粗い精度で十分なので iters=15 などに落とすと速い。
    """
    l_col = points[:, 0:1]
    ab = points[:, 1:3]
    n = points.shape[0]
    lo = np.zeros(n)
    hi = np.ones(n)
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        candidates = np.hstack([l_col, ab * mid[:, None]])
        linear = oklab_to_linear(candidates)
        valid = np.all((linear >= -tol) & (linear <= 1.0 + tol), axis=1)
        lo = np.where(valid, mid, lo)
        hi = np.where(valid, hi, mid)
    # 元々ガマット内の点では lo → 1.0 に収束するので、一律に ab * lo を掛けても
    # 元の値とほぼ同じに戻る（誤差は 2^-iters のオーダー）。
    return np.hstack([l_col, ab * lo[:, None]])


def _energy(
    flat_params: np.ndarray,
    base_oklab: np.ndarray,
    alpha: float,
    lambda_: float,
    eps: float = 1e-6,
) -> float:
    """3 項からなるエネルギー関数. すべて $1/d^2$（逆二乗）形.

    オプティマイザが箱 bounds の角（ガマット外の過彩度）に貼り付くのを
    防ぐため、距離計算は **クリップ後の座標** で行う。こうすると
    「最終的に表示される色」で距離が評価され、配置が現実的になる。
    最適化中の評価は粗い精度で十分なので iters=15 で二分探索を早く打ち切る。
    eps は二乗距離に足して零割と数値的急変を抑える。
    """
    points_raw = flat_params.reshape(-1, 3)
    points = _clip_to_gamut(points_raw, iters=15)

    # 第1項: 色同士のペアワイズ反発 (上三角だけ集計して重複を避ける)
    diff = points[:, None, :] - points[None, :, :]
    d_sq = np.sum(diff * diff, axis=-1)
    iu = np.triu_indices_from(d_sq, k=1)
    term1 = float(np.sum(1.0 / (d_sq[iu] + eps)))

    # 第2項: 背景色からの反発 (alpha が重み)
    d_base = np.sum((points - base_oklab) ** 2, axis=-1)
    term2 = alpha * float(np.sum(1.0 / (d_base + eps)))

    # 第3項: L 軸 (無彩色軸) からの反発 → グレーに近い色にペナルティ。
    # L 軸までの距離はクロマ sqrt(a^2 + b^2) そのもの。
    # 白黒からの反発項は、クリップ対応エネルギーでは L 端にオプティマイザが
    # 貼り付かないため冗長になり削除した。
    chroma_sq = points[:, 1] ** 2 + points[:, 2] ** 2
    term3 = lambda_ * float(np.sum(1.0 / (chroma_sq + eps)))

    return term1 + term2 + term3


class Palette(NamedTuple):
    hex_codes: list[str]
    oklab: np.ndarray


def generate_palette(
    num_colors: int,
    base_color: str,
    alpha: float = 1.0,
    lambda_: float = 1.0,
    seed: int = 0,
) -> Palette:
    """Oklab 空間で N 色を電荷反発モデルで配置し、hex コードで返す.

    alpha: 背景色反発の重み / lambda_: L 軸反発の重み /
    seed: 初期化ジッタの再現用シード.
    """
    if num_colors < 1:
        raise ValueError("num_colors must be >= 1")
    base_oklab = hex_to_oklab(base_color)

    # 初期配置: L=0.6 付近の円周上に等間隔。L に微小ジッタを加えるのは
    # 完全対称なサドル点に L-BFGS-B が嵌るのを避けるため (seed で再現可)。
    rng = np.random.default_rng(seed)
    theta = np.linspace(0.0, 2.0 * np.pi, num_colors, endpoint=False)
    L = 0.6 + rng.normal(0.0, 0.02, num_colors)
    a = 0.15 * np.cos(theta)
    b = 0.15 * np.sin(theta)
    x0 = np.stack([L, a, b], axis=1).reshape(-1)

    # L は [0.2, 0.9] に制限（極端な白黒を避ける）。(a, b) は sRGB ガマット
    # の外側まで余裕を持たせ、ガマット制約はエネルギー側のクリップで吸収。
    bounds = [(0.2, 0.9), (-0.4, 0.4), (-0.4, 0.4)] * num_colors
    result = minimize(
        _energy,
        x0,
        args=(base_oklab, alpha, lambda_),
        method="L-BFGS-B",
        bounds=bounds,
    )

    # 最終出力は高精度クリップ（iters=30）で sRGB→hex に変換する。
    points = result.x.reshape(-1, 3)
    clipped = _clip_to_gamut(points, iters=30)
    linear = oklab_to_linear(clipped)
    srgb = linear_to_srgb(linear)
    hex_codes = [srgb_to_hex(row) for row in srgb]
    return Palette(hex_codes=hex_codes, oklab=clipped)
