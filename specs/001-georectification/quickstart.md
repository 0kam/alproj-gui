# クイックスタート: オルソ化

**機能**: 001-georectification
**対象**: 開発者

## 前提条件

### システム要件

- macOS 12+ または Windows 10+
- Node.js 20+
- Python 3.11+
- Rust 1.75+（Tauri ビルド用）

### 必要なツール

```bash
# Node.js パッケージマネージャー
npm install -g pnpm

# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Tauri CLI
cargo install tauri-cli
```

## セットアップ

### 1. リポジトリクローン

```bash
git clone https://github.com/0kam/alproj-gui.git
cd alproj-gui
git checkout 001-georectification
```

### 2. フロントエンド依存関係

```bash
cd frontend
pnpm install
```

### 3. バックエンド依存関係

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 4. alproj インストール

```bash
pip install git+https://github.com/0kam/alproj.git
```

## 開発サーバー起動

### ターミナル 1: バックエンド

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8765
```

### ターミナル 2: フロントエンド + Tauri

```bash
cd frontend
pnpm tauri dev
```

ブラウザで `http://localhost:5173` が開き、Tauri ウィンドウが起動します。

## プロジェクト構造

```
alproj-gui/
├── frontend/          # Svelte + TypeScript
│   ├── src/
│   │   ├── lib/       # コンポーネント、ストア
│   │   └── routes/    # ページ
│   └── package.json
├── backend/           # Python + FastAPI
│   ├── app/
│   │   ├── api/       # API ルート
│   │   ├── models/    # データモデル
│   │   └── services/  # ビジネスロジック
│   └── pyproject.toml
├── src-tauri/         # Tauri (Rust)
│   └── src/main.rs
└── specs/             # 仕様書
```

## 基本的な開発フロー

### 1. 新しい API エンドポイント追加

```python
# backend/app/api/routes/example.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/example")
async def get_example():
    return {"message": "Hello"}
```

```python
# backend/app/main.py に追加
from app.api.routes import example
app.include_router(example.router, prefix="/api")
```

### 2. 新しいページ追加

```svelte
<!-- frontend/src/routes/example/+page.svelte -->
<script lang="ts">
  import { t } from '$lib/i18n';
</script>

<h1>{$t('example.title')}</h1>
```

```json
// frontend/src/lib/i18n/ja.json に追加
{
  "example": {
    "title": "サンプルページ"
  }
}
```

### 3. API クライアント生成

```bash
cd frontend
pnpm run generate-api  # OpenAPI から TypeScript 型生成
```

## テスト実行

### バックエンド

```bash
cd backend
pytest
pytest --cov=app  # カバレッジ付き
```

### フロントエンド

```bash
cd frontend
pnpm test        # Vitest
pnpm test:e2e    # Playwright
```

## ビルド

### 開発ビルド

```bash
cd frontend
pnpm tauri build --debug
```

### リリースビルド

```bash
# サイドカー（Python）ビルド
cd backend
pyinstaller --onefile app/main.py -n alproj-sidecar

# Tauri ビルド
cd frontend
pnpm tauri build
```

成果物:
- macOS: `frontend/src-tauri/target/release/bundle/dmg/`
- Windows: `frontend/src-tauri/target/release/bundle/msi/`

## トラブルシューティング

### バックエンドが起動しない

```bash
# ポート確認
lsof -i :8765

# 依存関係再インストール
pip install -e ".[dev]" --force-reinstall
```

### Tauri ビルドエラー

```bash
# Rust ツールチェーン更新
rustup update

# Tauri CLI 更新
cargo install tauri-cli --force
```

### alproj インポートエラー

```bash
# 依存関係確認
pip show alproj
pip install opencv-python-headless  # GUI 環境でない場合
```

## 関連ドキュメント

- [仕様書](./spec.md)
- [実装計画](./plan.md)
- [データモデル](./data-model.md)
- [API 仕様](./contracts/openapi.yaml)
- [alproj ドキュメント](https://github.com/0kam/alproj)

