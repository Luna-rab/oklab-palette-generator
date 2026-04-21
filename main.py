import argparse

from src.palette import generate_palette
from src.visualize import plot_palette


def main() -> None:
    parser = argparse.ArgumentParser(description="Oklab カラーパレット生成デモ")
    parser.add_argument(
        "-n", "--num-colors", type=int, default=12, help="生成する色の数 (デフォルト: 12)"
    )
    parser.add_argument(
        "-b",
        "--base",
        default="#1e1e2e",
        help="背景色の Hex コード (デフォルト: #1e1e2e)",
    )
    parser.add_argument(
        "--plot",
        nargs="?",
        const="palette.png",
        default=None,
        help="Oklab 空間の 3D 散布図を画像ファイルに保存 (パス省略時: palette.png)",
    )
    args = parser.parse_args()

    palette = generate_palette(num_colors=args.num_colors, base_color=args.base)
    for hex_code in palette.hex_codes:
        print(hex_code)

    if args.plot is not None:
        plot_palette(palette, save_path=args.plot, base_color=args.base)
        print(f"plot: {args.plot}")


if __name__ == "__main__":
    main()
