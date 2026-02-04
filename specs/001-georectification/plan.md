# 実装計画: オルソ化

**ブランチ**: `001-georectification` | **日付**: 2025-01-27 | **仕様書**: [spec.md](./spec.md)
**入力**: `/specs/001-georectification/spec.md`

## 概要

景観写真を地理座標付き画像（GeoTIFF）に変換するオルソ化機能を実装する。
ウィザード形式のUIで非技術者でも操作可能にし、地図上でカメラパラメータを直感的に設定できるようにする。
alproj ライブラリをコアとして使用し、Tauri + Svelte + FastAPI のアーキテクチャで構築する。

## 技術コンテキスト

**言語/バージョン**:
- フロントエンド: TypeScript 5.x + Svelte 5.x
- バックエンド: Python 3.11+
- シェル: Rust (Tauri 2.x)

**主要依存関係**:
- フロントエンド: Svelte, Tailwind CSS, MapLibre GL JS（地図）
- バックエンド: FastAPI, alproj, rasterio, numpy, opencv-python
- ビルド: PyInstaller, Tauri CLI

**ストレージ**: ファイルベース（.alproj プロジェクトファイル、JSON形式）

**テスト**:
- Python: pytest
- フロントエンド: Vitest + Playwright
- E2E: Playwright

**ターゲットプラットフォーム**: macOS, Windows（Linux は低優先度）

**プロジェクトタイプ**: デスクトップアプリ（Tauri + サイドカー）

**パフォーマンス目標**:
- シミュレーション画像プレビュー: 2秒以内（1000x1000px）
- 地図操作: 60fps
- UI応答: 100ms以内

**制約**:
- インストーラーサイズ: 500MB未満
- メモリ使用量: 4GB以下（処理中ピーク時）
- オフライン動作必須（地図タイル除く）

**スケール/スコープ**:
- 画面数: 約10画面（ウィザード5ステップ + 設定/結果画面）
- 同時処理: 1プロジェクト（バッチ処理は将来対応）

## 憲法チェック

*ゲート: Phase 0 開始前に合格必須。Phase 1 設計後に再チェック。*

| 原則 | 要件 | 状態 | 対応 |
|------|------|------|------|
| I. ユーザー中心設計 | ウィザード形式、詳細は非表示、進捗表示 | ✅ 準拠 | spec で定義済み |
| II. レイヤー分離 | Tauri → Svelte → FastAPI → alproj | ✅ 準拠 | 4層構造で設計 |
| III. 非同期処理 | 画像処理はバックグラウンド、進捗/キャンセル対応 | ✅ 準拠 | ジョブキュー設計に含む |
| IV. 拡張性 | UIページ登録可能、プロジェクトファイルバージョン管理 | ✅ 準拠 | 設計に組み込み |
| V. クロスプラットフォーム | macOS/Windows インストーラー | ✅ 準拠 | Tauri + PyInstaller |
| VI. 国際化 | 日本語UI、翻訳ファイル管理、UTC内部/JST表示 | ✅ 準拠 | i18n 設計に含む |

**ゲート結果**: ✅ 合格 - Phase 0 に進む

## プロジェクト構造

### ドキュメント（この機能）

```text
specs/001-georectification/
├── plan.md              # このファイル
├── research.md          # Phase 0 出力
├── data-model.md        # Phase 1 出力
├── quickstart.md        # Phase 1 出力
├── contracts/           # Phase 1 出力（OpenAPI）
└── tasks.md             # Phase 2 出力（/speckit.tasks）
```

### ソースコード（リポジトリルート）

```text
src-tauri/                    # Tauri シェル (Rust)
├── src/
│   └── main.rs              # サイドカー起動、IPC設定
├── Cargo.toml
└── tauri.conf.json

frontend/                     # フロントエンド (Svelte + TypeScript)
├── src/
│   ├── lib/
│   │   ├── components/      # 再利用可能コンポーネント
│   │   │   ├── Map/         # 地図関連
│   │   │   ├── ImageViewer/ # 画像表示
│   │   │   └── common/      # 共通UI
│   │   ├── stores/          # Svelte stores（状態管理）
│   │   ├── services/        # API クライアント
│   │   ├── i18n/            # 翻訳ファイル
│   │   │   └── ja.json
│   │   └── types/           # TypeScript 型定義
│   ├── routes/              # SvelteKit ページ
│   │   ├── +layout.svelte
│   │   ├── +page.svelte     # ホーム
│   │   └── georectify/      # オルソ化
│   │       ├── +page.svelte
│   │       └── steps/       # ウィザードステップ
│   └── app.html
├── static/
├── package.json
├── svelte.config.js
├── tailwind.config.js
└── vite.config.ts

backend/                      # バックエンド (Python + FastAPI)
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI アプリ
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── projects.py  # プロジェクト CRUD
│   │   │   ├── georectify.py # オルソ化処理
│   │   │   └── files.py     # ファイル読み込み
│   │   └── deps.py          # 依存性注入
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # 設定
│   │   └── jobs.py          # ジョブキュー
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py       # プロジェクトモデル
│   │   ├── camera.py        # カメラパラメータ
│   │   └── gcp.py           # GCP モデル
│   ├── services/
│   │   ├── __init__.py
│   │   ├── georectify.py    # alproj ラッパー
│   │   ├── raster.py        # ラスタ処理
│   │   └── project_io.py    # プロジェクト保存/読込
│   └── schemas/
│       ├── __init__.py
│       └── *.py             # Pydantic スキーマ
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml
└── requirements.txt

scripts/                      # ビルド/開発スクリプト
├── build-sidecar.sh         # PyInstaller でサイドカービルド
└── dev.sh                   # 開発サーバー起動
```

**構造決定**: Tauri + フロントエンド + バックエンドサイドカーの3層構造。
憲法のレイヤー分離アーキテクチャに準拠し、各レイヤーが独立してテスト可能。

## 自動保存/復旧設計

**目的**: 処理中のアプリ強制終了からのデータ損失を防ぐ

**設計**:
- 処理開始前に現在のプロジェクト状態を一時ファイル（`.alproj.tmp`）として自動保存
- 一時ファイルの保存場所: ユーザーデータディレクトリ（`~/.alproj/recovery/`）
- 処理正常完了時に一時ファイルを削除
- アプリ起動時に一時ファイルの存在をチェック

**復旧フロー**:
1. アプリ起動時に `~/.alproj/recovery/` 内の `.alproj.tmp` ファイルを検索
2. 見つかった場合、復旧ダイアログを表示
   - 「復旧する」: 一時ファイルからプロジェクト状態を復元
   - 「破棄する」: 一時ファイルを削除して新規開始
3. 復旧後は通常のプロジェクトとして継続

**制約**:
- 処理途中の中間結果は保存しない（処理開始前の状態のみ）
- 複数の一時ファイルがある場合は最新のものを優先提示

## 複雑性トラッキング

> 憲法違反がある場合のみ記入

該当なし - すべての原則に準拠

