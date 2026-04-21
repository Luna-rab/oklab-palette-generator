"""Oklab 色空間でのパレット可視化."""

import matplotlib

# Devcontainer は display なし環境が多いため非対話バックエンドで描画する.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

from src.palette import Palette, hex_to_oklab  # noqa: E402


def plot_palette(
    palette: Palette,
    save_path: str,
    base_color: str | None = None,
) -> None:
    """色相環 (a-b 平面) とパレット帯で可視化して画像を保存する.

    色相環は Oklab 空間を L 軸方向に射影した図: 角度が色相, 半径がクロマ.
    点のサイズで明度 L を表現し (大きいほど明るい), 各点は自身の色で塗る.
    右側のパレット帯は実際の並び順で色見本と Hex/L/C/h 値を添える.
    """
    fig = plt.figure(figsize=(14, 7))
    gs = GridSpec(1, 2, width_ratios=[1, 1], figure=fig, wspace=0.1)

    _draw_hue_wheel(fig.add_subplot(gs[0, 0]), palette, base_color)
    _draw_palette_strip(fig.add_subplot(gs[0, 1]), palette)

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _draw_hue_wheel(
    ax: plt.Axes,
    palette: Palette,
    base_color: str | None,
) -> None:
    a_vals = palette.oklab[:, 1]
    b_vals = palette.oklab[:, 2]
    L_vals = palette.oklab[:, 0]

    # 軸レンジは最大クロマに合わせて自動調整 (背景色含む)
    chroma_all = np.sqrt(a_vals**2 + b_vals**2)
    if base_color is not None:
        base = hex_to_oklab(base_color)
        chroma_all = np.append(chroma_all, float(np.sqrt(base[1] ** 2 + base[2] ** 2)))
    max_chroma = max(0.15, float(np.max(chroma_all)) * 1.15)

    # 参照用の同心円 (クロマ目盛り)
    for c in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
        if c <= max_chroma:
            ax.add_patch(
                Circle(
                    (0, 0),
                    c,
                    fill=False,
                    edgecolor="gray",
                    alpha=0.3,
                    linestyle="--",
                    linewidth=0.6,
                )
            )
            ax.text(c * 0.707, c * 0.707, f"{c:.2f}", fontsize=7, color="gray", alpha=0.6)

    # 参照用の放射線 (色相 30° 刻み)
    for angle_deg in range(0, 360, 30):
        angle = np.radians(angle_deg)
        ax.plot(
            [0, max_chroma * np.cos(angle)],
            [0, max_chroma * np.sin(angle)],
            color="gray",
            alpha=0.2,
            linewidth=0.5,
        )

    # 原点 (L 軸の射影位置 = 無彩色)
    ax.plot(0, 0, "k+", markersize=12, markeredgewidth=1.5, zorder=3)

    # 点: 色は自身の hex, サイズは L (暗い色は小さく, 明るい色は大きく)
    sizes = 80 + 420 * L_vals
    ax.scatter(
        a_vals,
        b_vals,
        c=palette.hex_codes,
        s=sizes,
        edgecolors="black",
        linewidths=0.8,
        zorder=4,
    )

    # 背景色は星マーカーで区別
    if base_color is not None:
        base = hex_to_oklab(base_color)
        ax.scatter(
            [base[1]],
            [base[2]],
            c=base_color,
            s=350,
            marker="*",
            edgecolors="black",
            linewidths=1.2,
            zorder=5,
            label=f"base {base_color}",
        )
        ax.legend(loc="upper right", fontsize=9)

    ax.set_xlabel("a  (green ↔ red)")
    ax.set_ylabel("b  (blue ↔ yellow)")
    ax.set_title("Hue wheel  (a-b projection, size ∝ L)", fontsize=11)
    ax.set_xlim(-max_chroma, max_chroma)
    ax.set_ylim(-max_chroma, max_chroma)
    ax.set_aspect("equal")
    ax.axhline(0, color="gray", alpha=0.2, linewidth=0.5)
    ax.axvline(0, color="gray", alpha=0.2, linewidth=0.5)


def _draw_palette_strip(ax: plt.Axes, palette: Palette) -> None:
    n = len(palette.hex_codes)
    for i, hex_code in enumerate(palette.hex_codes):
        y = n - 1 - i  # 上から順に並べる
        ax.add_patch(Rectangle((0, y), 1, 1, facecolor=hex_code, edgecolor="black", linewidth=0.5))
        L_i = float(palette.oklab[i, 0])
        a_i = float(palette.oklab[i, 1])
        b_i = float(palette.oklab[i, 2])
        chroma_i = float(np.sqrt(a_i**2 + b_i**2))
        hue_deg = float(np.degrees(np.arctan2(b_i, a_i))) % 360.0
        ax.text(
            1.15,
            y + 0.5,
            f"{hex_code}   L={L_i:.2f}   C={chroma_i:.2f}   h={hue_deg:3.0f}°",
            va="center",
            fontfamily="monospace",
            fontsize=10,
        )

    ax.set_xlim(-0.1, 5.5)
    ax.set_ylim(-0.1, n + 0.1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Palette  (L=lightness, C=chroma, h=hue°)", fontsize=11)
