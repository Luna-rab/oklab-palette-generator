# Oklab 電荷反発モデルによるカラーパレット生成器

人間の知覚的に等間隔で、背景色や無彩色から明確に区別できる $N$ 色のパレットを、**Oklab 色空間上の電荷反発モデル**でエネルギー最小化して動的に生成する。

## アルゴリズム

### 変数

$N$ 個の点の Oklab 座標 $(L, a, b)$ を $3N$ 次元の変数ベクトルとして扱い、`scipy.optimize.minimize` (L-BFGS-B) でエネルギーを最小化する。

### エネルギー関数

$$E = \sum_{i<j} \frac{1}{\|C_i-C_j\|^2} + \alpha \sum_i \frac{1}{\|C_i-C_{\text{base}}\|^2} + \lambda \sum_i \frac{1}{a_i^2+b_i^2}$$

- **第 1 項**: 色同士のペアワイズ反発
- **第 2 項**: 背景色からの反発（重み $\alpha$）
- **第 3 項**: L 軸（無彩色軸）からの距離の逆数＝クロマの逆数。グレーに近い色にペナルティ

各項は $1/d^2$（逆二乗）形。分母に小さな $\varepsilon$ を加えて零割と数値的急変を抑える。

### 制約

- $L$ は $[0.2, 0.9]$ に制限（極端な白黒を避ける）— L-BFGS-B の box bounds で処理
- $(a, b)$ は $[-0.4, 0.4]$ の box bounds（sRGB ガマット外にも余裕を持たせる）
- sRGB ガマット制約は **エネルギー関数側で吸収**（次節）

### クリップ対応エネルギー

`_energy` 内で距離計算の **前** に全点を `_clip_to_gamut` でガマット内に写す。これにより「最終的に表示される色」の座標で距離が評価され、オプティマイザは sRGB ガマット内に収まる配置を直接探索する（box bounds の角＝過彩度コーナー解に貼り付かない）。

### 色空間変換

Oklab 変換は Björn Ottosson の標準行列を float64 定数としてインライン実装（`colour-science` 等の外部ライブラリ不使用）。

```
hex ─→ sRGB ─(gamma decode)─→ linear RGB ─(M1)─→ LMS ─(cbrt)─→ L'M'S' ─(M2)─→ Oklab
```

- 逆変換は `_M1_INV`, `_M2_INV` で対称に行う
- 負値 LMS を扱うため `np.cbrt` を使う（`** (1/3)` は負値で NaN）

### ガマットクリップ

`_clip_to_gamut(points, iters)` は $L$ を保ったまま $(a, b)$ を原点方向に縮める倍率を **二分探索** で求める。全 $N$ 点を並列に処理（numpy のバッチ演算、Python ループなし）。

- ガマット判定は **linear RGB 空間** で行う（sRGB 空間は非線形なので立方体にならない）
- `iters` で精度／速度をトレードオフ:
  - 最適化中の評価: **15 反復**
  - 最終出力: **30 反復**（$\approx$ 1e-9 精度）
- 元々ガマット内の点は倍率 `lo` が 1.0 に収束するので、一律に倍率を掛けても実質的に元の値が返る（誤差 $2^{-\text{iters}}$ のオーダー）

### 初期化

$L=0.6$ 付近の円周（半径 0.15）上に $N$ 個の点を等間隔配置。$L$ には小さなジッタ（$\sigma=0.02$）を加えて、完全対称なサドル点に L-BFGS-B が嵌るのを避ける。`seed` 引数で再現可能。

## 使い方

### ライブラリとして

```python
from src.palette import generate_palette

palette = generate_palette(
    num_colors=12,
    base_color="#1e1e2e",
    alpha=1.0,          # 背景色反発の重み
    lambda_=1.0,        # L 軸反発の重み
    seed=0,             # 初期化乱数シード
)

for hex_code in palette.hex_codes:
    print(hex_code)

# palette.hex_codes: list[str]
# palette.oklab: np.ndarray, shape (N, 3)
```

### 可視化

`src/visualize.py` の `plot_palette` で、色相環（a-b 射影）とパレット帯の 2 パネル構成の図を画像ファイルに保存できる。

```python
from src.visualize import plot_palette

plot_palette(palette, save_path="palette.png", base_color="#1e1e2e")
```

- **色相環**: a-b 平面に各色を配置。サイズで L（明度）を表現し、背景色は★マーカーで重ねる
- **パレット帯**: 実際の並び順で色見本を縦に積み、Hex / L / C（クロマ）/ h（色相角°）を併記

### CLI

```bash
uv run python main.py                             # デフォルト (N=12, base=#1e1e2e)
uv run python main.py -n 24 -b '#ffffff'          # 色数と背景色を指定
uv run python main.py --plot                      # palette.png に図を保存
uv run python main.py -n 8 -b '#282828' --plot out.png  # 全指定
```

| フラグ | 説明 |
| --- | --- |
| `-n`, `--num-colors` | 生成する色の数（デフォルト: 12） |
| `-b`, `--base` | 背景色 Hex コード（デフォルト: `#1e1e2e`） |
| `--plot [PATH]` | 色相環＋パレット帯を画像保存（パス省略時: `palette.png`） |

## 開発環境

Python 3.14 / uv / ruff / ty を用いた Dev Container 構成。

```bash
uv sync                       # 依存インストール
uv run python main.py         # デモ実行
uv run ruff format .          # フォーマット
uv run ruff check --fix .     # lint + 自動修正
uv run ty check               # 型チェック
```

### 含まれるもの

- **ベースイメージ**: `mcr.microsoft.com/devcontainers/base:ubuntu`
- **パッケージマネージャ**: [uv](https://docs.astral.sh/uv/)
- **Python**: `>=3.14`
- **リンタ / フォーマッタ**: [ruff](https://docs.astral.sh/ruff/)（`ANN` ルールで型注釈を強制）
- **型チェッカ**: [ty](https://docs.astral.sh/ty/)
- **ランタイム依存**: numpy, scipy, matplotlib
- **追加機能**: git / GitHub CLI / AWS CLI / Docker-in-Docker
- **VS Code 拡張**: `ms-python.python`, `charliermarsh.ruff`, `astral-sh.ty` ほか

### 開発ワークフロー

- **保存時**: ruff が自動フォーマット + import 整列 + lint 自動修正
- **編集後フック** (`.claude/post-edit-hook.sh`): Claude Code がファイルを編集するたびに `ruff format` → `ruff check --fix` → `ty check` が走り、違反があれば差し戻される
