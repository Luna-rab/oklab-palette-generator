#!/bin/bash
# post-edit-hook.sh
# ファイル編集後に Python ファイルへ ruff format / ruff check / ty check を実行する

set +e

INPUT=$(cat)

if command -v jq &> /dev/null; then
    EDITED_FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
fi

if [ -z "$EDITED_FILE" ] || [ ! -f "$EDITED_FILE" ]; then
    exit 0
fi

# .py ファイル以外は無視
if [[ "$EDITED_FILE" != *.py ]]; then
    exit 0
fi

WORK_DIR="$CLAUDE_PROJECT_DIR"

# プロジェクト外のファイルは無視
if [[ "$EDITED_FILE" != "$WORK_DIR"/* ]]; then
    exit 0
fi

cd "$WORK_DIR" || exit 0
RELATIVE_FILE="${EDITED_FILE#$WORK_DIR/}"

RUFF="$WORK_DIR/.venv/bin/ruff"
TY="$WORK_DIR/.venv/bin/ty"

# venv が未作成なら何もしない (uv sync 前の状態など)
if [ ! -x "$RUFF" ] || [ ! -x "$TY" ]; then
    exit 0
fi

echo "🔍 Checking Python file: $RELATIVE_FILE"

# フォーマット (editor.formatOnSave 相当)
if ! "$RUFF" format "$RELATIVE_FILE"; then
    exit 2
fi
echo "✅ Ruff format passed"

# リント自動修正 (source.fixAll / source.organizeImports 相当)
if ! "$RUFF" check --fix "$RELATIVE_FILE"; then
    exit 2
fi
echo "✅ Ruff check passed"

# 型チェック (ty の出力は stdout に出るため stderr にリダイレクト)
if ! "$TY" check "$RELATIVE_FILE" 2>&1 1>&2; then
    exit 2
fi
echo "✅ ty type check passed"

exit 0
