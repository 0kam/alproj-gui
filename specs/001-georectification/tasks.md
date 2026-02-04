# タスク一覧: オルソ化

**入力**: `/specs/001-georectification/` のドキュメント
**前提**: plan.md, spec.md, data-model.md, contracts/openapi.yaml

**テスト**: テストタスクは明示的に要求されていないため省略

**構成**: ユーザーストーリーごとにグループ化し、独立した実装・テストを可能にする

## フォーマット: `[ID] [P?] [Story?] 説明`

- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: 所属するユーザーストーリー（US1, US2, US3）
- ファイルパスを含めること

## パス規約

```
src-tauri/           # Tauri シェル (Rust)
frontend/src/        # フロントエンド (Svelte + TypeScript)
backend/app/         # バックエンド (Python + FastAPI)
```

---

## Phase 1: セットアップ

**目的**: プロジェクト初期化と基本構造の構築

- [X] T001 Tauri + SvelteKit プロジェクトを初期化する（frontend/, src-tauri/）
- [X] T002 [P] Python バックエンドプロジェクトを初期化する（backend/pyproject.toml, backend/app/__init__.py）
- [X] T003 [P] フロントエンド依存関係をインストールする（Svelte, Tailwind CSS, MapLibre GL JS）in frontend/package.json
- [X] T004 [P] バックエンド依存関係を設定する（FastAPI, alproj, rasterio）in backend/pyproject.toml
- [X] T005 [P] フロントエンドの linting/formatting を設定する（ESLint, Prettier）in frontend/
- [X] T006 [P] バックエンドの linting/formatting を設定する（ruff, mypy）in backend/pyproject.toml
- [X] T007 開発スクリプトを作成する（scripts/dev.sh）

---

## Phase 2: 基盤構築（ブロッキング）

**目的**: すべてのユーザーストーリーに必要な共通インフラ

**⚠️ 重要**: このフェーズが完了するまでユーザーストーリーの作業は開始できない

### バックエンド基盤

- [X] T008 FastAPI アプリケーションエントリーポイントを作成する in backend/app/main.py
- [X] T009 [P] 設定管理モジュールを作成する in backend/app/core/config.py
- [X] T010 [P] ジョブキュー基盤を実装する in backend/app/core/jobs.py
- [X] T011 [P] 共通エラーハンドリングを実装する in backend/app/api/deps.py
- [X] T012 ヘルスチェックエンドポイントを実装する in backend/app/main.py

### 共通モデル/スキーマ

- [X] T013 [P] Project モデルを作成する in backend/app/models/project.py
- [X] T014 [P] CameraParams モデルを作成する in backend/app/models/camera.py
- [X] T015 [P] GCP モデルを作成する in backend/app/models/gcp.py
- [X] T016 [P] Pydantic スキーマを作成する in backend/app/schemas/project.py
- [X] T017 [P] Pydantic スキーマを作成する in backend/app/schemas/camera.py
- [X] T018 [P] Pydantic スキーマを作成する in backend/app/schemas/gcp.py
- [X] T019 [P] Pydantic スキーマを作成する in backend/app/schemas/job.py

### フロントエンド基盤

- [X] T020 [P] i18n セットアップと日本語翻訳ファイルを作成する in frontend/src/lib/i18n/
- [X] T021 [P] API クライアント基盤を作成する in frontend/src/lib/services/api.ts
- [X] T022 [P] 共通 UI コンポーネントを作成する in frontend/src/lib/components/common/
- [X] T023 [P] TypeScript 型定義を作成する in frontend/src/lib/types/
- [X] T024 メインレイアウトを作成する in frontend/src/routes/+layout.svelte
- [X] T025 ホームページを作成する in frontend/src/routes/+page.svelte

### Tauri 連携

- [X] T026 Tauri メイン設定を行う in src-tauri/tauri.conf.json
- [X] T027 サイドカー起動ロジックを実装する in src-tauri/src/lib.rs

**チェックポイント**: 基盤完了 - ユーザーストーリー実装を開始可能

---

## Phase 3: ユーザーストーリー 1 - 基本的なオルソ化 (P1) 🎯 MVP

**目標**: サンプルデータで GeoTIFF を出力できる基本フロー

**独立テスト**: DSM、航空写真、景観写真を入力し、GeoTIFF が出力されることを確認

### バックエンド API

- [X] T028 [P] [US1] ラスタファイル情報取得サービスを実装する in backend/app/services/raster.py
- [X] T029 [P] [US1] 画像ファイル情報取得サービスを実装する in backend/app/services/raster.py
- [X] T083 [P] [US1] EXIF 読み取りサービスを実装する（GPS位置→x,y,z、焦点距離→FOV推定）in backend/app/services/exif.py
- [X] T030 [US1] ファイル API ルートを実装する in backend/app/api/routes/files.py
- [X] T031 [US1] alproj ラッパーサービスを実装する in backend/app/services/georectify.py
- [X] T032 [US1] シミュレーション画像生成エンドポイントを実装する in backend/app/api/routes/georectify.py
- [X] T033 [US1] オルソ化処理エンドポイントを実装する in backend/app/api/routes/georectify.py
- [X] T084 [US1] 処理開始前の自動保存機能を実装する in backend/app/services/recovery.py
- [X] T034 [US1] WebSocket 進捗通知を実装する in backend/app/api/routes/georectify.py
- [X] T035 [US1] GeoTIFF エクスポートエンドポイントを実装する in backend/app/api/routes/georectify.py
- [X] T036 [US1] ジョブ状態取得/キャンセルエンドポイントを実装する in backend/app/api/routes/jobs.py

### フロントエンド - ウィザード

- [X] T037 [US1] ウィザード状態管理ストアを作成する in frontend/src/lib/stores/wizard.ts
- [X] T038 [US1] ウィザードレイアウトを作成する in frontend/src/routes/georectify/+layout.svelte
- [X] T039 [US1] ウィザードメインページを作成する in frontend/src/routes/georectify/+page.svelte

### フロントエンド - Step 1: データ入力

- [X] T040 [P] [US1] ファイル選択コンポーネントを作成する in frontend/src/lib/components/common/FileSelect.svelte
- [X] T041 [P] [US1] 画像プレビューコンポーネントを作成する in frontend/src/lib/components/ImageViewer/ImagePreview.svelte
- [X] T042 [US1] データ入力ステップページを作成する in frontend/src/routes/georectify/steps/data-input/+page.svelte
- [X] T043 [US1] ファイル情報表示（CRS、サイズ、範囲）を実装する in frontend/src/routes/georectify/steps/data-input/+page.svelte

### フロントエンド - Step 2: カメラ設定（地図）

- [X] T044 [P] [US1] MapLibre 地図コンポーネントを作成する in frontend/src/lib/components/Map/MapView.svelte
- [X] T045 [P] [US1] カメラ位置マーカーコンポーネントを作成する in frontend/src/lib/components/Map/CameraMarker.svelte
- [X] T046 [P] [US1] 視野扇形描画コンポーネントを作成する in frontend/src/lib/components/Map/FovCone.svelte
- [X] T047 [US1] カメラパラメータ入力フォームを作成する in frontend/src/lib/components/common/CameraParamsForm.svelte
- [X] T048 [US1] シミュレーション画像プレビューを実装する in frontend/src/lib/components/ImageViewer/SimulationPreview.svelte
- [X] T049 [US1] カメラ設定ステップページを作成する in frontend/src/routes/georectify/steps/camera-setup/+page.svelte

### フロントエンド - Step 3: 処理実行

- [X] T050 [P] [US1] 進捗バーコンポーネントを作成する in frontend/src/lib/components/common/ProgressBar.svelte
- [X] T051 [P] [US1] 処理ログ表示コンポーネントを作成する in frontend/src/lib/components/common/ProcessLog.svelte
- [X] T052 [US1] WebSocket 接続管理を実装する in frontend/src/lib/services/websocket.ts
- [X] T053 [US1] 処理実行ステップページを作成する in frontend/src/routes/georectify/steps/processing/+page.svelte

### フロントエンド - Step 4: 結果確認

- [X] T054 [P] [US1] 精度指標表示コンポーネントを作成する in frontend/src/lib/components/common/MetricsDisplay.svelte
- [X] T055 [P] [US1] 画像比較コンポーネントを作成する（元画像と補正後画像の重ね合わせ表示対応）in frontend/src/lib/components/ImageViewer/ImageCompare.svelte
- [X] T056 [US1] 結果確認ステップページを作成する in frontend/src/routes/georectify/steps/result/+page.svelte

### フロントエンド - Step 5: エクスポート

- [X] T057 [US1] エクスポート設定フォームを作成する（解像度、出力座標系指定対応）in frontend/src/lib/components/common/ExportForm.svelte
- [X] T058 [US1] エクスポートステップページを作成する in frontend/src/routes/georectify/steps/export/+page.svelte

**チェックポイント**: US1 完了 - サンプルデータで GeoTIFF 出力が可能

---

## Phase 4: ユーザーストーリー 2 - 詳細調整 (P2)

**目標**: GCP の編集とパラメータ再調整で精度向上

**独立テスト**: 自動処理後に GCP を除外して再処理し、RMSE が変化することを確認

### バックエンド API

- [X] T059 [US2] プロジェクト更新（カメラパラメータ変更）エンドポイントを実装する in backend/app/api/routes/projects.py
- [X] T060 [US2] 部分再処理（指定ステップから）機能を実装する in backend/app/services/georectify.py

### フロントエンド - 詳細設定パネル

- [X] T061 [P] [US2] GCP 一覧テーブルコンポーネントを作成する in frontend/src/lib/components/common/GcpTable.svelte
- [X] T062 [P] [US2] GCP 地図表示コンポーネントを作成する in frontend/src/lib/components/Map/GcpOverlay.svelte
- [X] T063 [US2] 詳細設定パネルを作成する in frontend/src/lib/components/common/AdvancedSettings.svelte
- [X] T064 [US2] マッチングアルゴリズム選択 UI を実装する in frontend/src/lib/components/common/AdvancedSettings.svelte
- [X] T065 [US2] 最適化パラメータ調整 UI を実装する in frontend/src/lib/components/common/AdvancedSettings.svelte
- [X] T066 [US2] 結果画面に詳細設定パネルを統合する in frontend/src/routes/georectify/steps/result/+page.svelte

**チェックポイント**: US2 完了 - 詳細調整による精度向上が可能

---

## Phase 5: ユーザーストーリー 3 - プロジェクト保存/再開 (P3)

**目標**: プロジェクトを .alproj ファイルに保存し、後から再開できる

**独立テスト**: プロジェクトを保存、アプリ再起動後に開いて、すべての状態が復元されることを確認

### バックエンド API

- [X] T067 [P] [US3] プロジェクト保存サービスを実装する in backend/app/services/project_io.py
- [X] T068 [P] [US3] プロジェクト読み込みサービスを実装する in backend/app/services/project_io.py
- [X] T069 [US3] プロジェクトファイルバージョン管理/マイグレーションを実装する in backend/app/services/project_io.py
- [X] T070 [US3] プロジェクト CRUD エンドポイントを実装する in backend/app/api/routes/projects.py
- [X] T071 [US3] プロジェクト保存/開くエンドポイントを実装する in backend/app/api/routes/projects.py

### フロントエンド - プロジェクト管理

- [X] T072 [P] [US3] プロジェクト一覧コンポーネントを作成する in frontend/src/lib/components/common/ProjectList.svelte
- [X] T073 [P] [US3] プロジェクト状態ストアを作成する in frontend/src/lib/stores/project.ts
- [X] T074 [US3] ホームページにプロジェクト一覧を統合する in frontend/src/routes/+page.svelte
- [X] T075 [US3] ファイル保存/開くダイアログを実装する in frontend/src/lib/services/file-dialog.ts
- [X] T076 [US3] メニューバーに保存/開くを追加する in frontend/src/routes/+layout.svelte
- [X] T085 [US3] 起動時の復旧ダイアログを実装する in frontend/src/lib/components/common/RecoveryDialog.svelte
- [X] T086 [US3] 復旧チェック API エンドポイントを実装する in backend/app/api/routes/recovery.py

**チェックポイント**: US3 完了 - プロジェクト保存と再開が可能

---

## Phase 6: 仕上げとクロスカッティング

**目的**: 全体の品質向上と最終調整

- [X] T077 [P] エラーメッセージを日本語化する in frontend/src/lib/i18n/ja.json
- [X] T078 [P] ヘルプテキストとツールチップを追加する in frontend/src/lib/i18n/ja.json
- [X] T087 [P] メモリ不足エラー時の推奨解像度提示メッセージを実装する in backend/app/services/georectify.py
- [X] T088 [P] マッチング失敗時の対処法提案メッセージを実装する in backend/app/services/georectify.py
- [X] T089 [P] 処理レポート出力機能を実装する（使用パラメータ、精度指標をJSON/テキスト形式で出力）in backend/app/services/report.py
- [X] T079 アプリアイコンとスプラッシュ画面を設定する in src-tauri/
- [X] T080 サイドカービルドスクリプトを作成する in scripts/build-sidecar.sh
- [X] T081 Tauri ビルド設定を完成させる in src-tauri/tauri.conf.json
- [X] T082 サンプルデータとチュートリアルを用意する in docs/

---

## 依存関係と実行順序

### フェーズ依存関係

- **Phase 1 (セットアップ)**: 依存なし - 即座に開始可能
- **Phase 2 (基盤)**: Phase 1 完了後 - 全ユーザーストーリーをブロック
- **Phase 3 (US1)**: Phase 2 完了後 - MVP
- **Phase 4 (US2)**: Phase 2 完了後 - US1 と並列可能だが、US1 後が推奨
- **Phase 5 (US3)**: Phase 2 完了後 - US1/US2 と並列可能
- **Phase 6 (仕上げ)**: すべてのユーザーストーリー完了後

### ユーザーストーリー依存関係

- **US1 (P1)**: 独立 - MVP として最初に完了すべき
- **US2 (P2)**: US1 の結果画面を拡張するため、US1 後が推奨
- **US3 (P3)**: 独立 - ただし保存対象となる状態が必要なため US1 後が推奨

### 各ストーリー内の順序

1. バックエンド API（モデル → サービス → ルート）
2. フロントエンド（コンポーネント → ページ → 統合）

### 並列実行の機会

- Phase 1: T002, T003, T004, T005, T006 は並列実行可能
- Phase 2: モデル (T013-T019) とフロントエンド基盤 (T020-T025) は並列実行可能
- Phase 3: 各ステップのコンポーネント作成は並列実行可能

---

## 並列実行例

```bash
# Phase 2 のモデル作成を並列実行:
Task: "Project モデルを作成する in backend/app/models/project.py"
Task: "CameraParams モデルを作成する in backend/app/models/camera.py"
Task: "GCP モデルを作成する in backend/app/models/gcp.py"

# Phase 3 Step 2 のコンポーネント作成を並列実行:
Task: "MapLibre 地図コンポーネントを作成する in frontend/src/lib/components/Map/MapView.svelte"
Task: "カメラ位置マーカーコンポーネントを作成する in frontend/src/lib/components/Map/CameraMarker.svelte"
Task: "視野扇形描画コンポーネントを作成する in frontend/src/lib/components/Map/FovCone.svelte"
```

---

## 実装戦略

### MVP ファースト (US1 のみ)

1. Phase 1 完了: セットアップ
2. Phase 2 完了: 基盤（すべてのストーリーをブロック）
3. Phase 3 完了: US1 - 基本的なオルソ化
4. **停止して検証**: サンプルデータで GeoTIFF が出力できることを確認
5. デモ/リリース可能

### インクリメンタルデリバリー

1. Setup + 基盤 → 基盤完了
2. US1 追加 → 独立テスト → MVP リリース
3. US2 追加 → 独立テスト → 詳細調整機能追加
4. US3 追加 → 独立テスト → プロジェクト管理機能追加
5. 各ストーリーは独立して価値を提供

---

## 備考

- [P] タスク = 異なるファイル、依存関係なし
- [Story] ラベル = ユーザーストーリーへのトレーサビリティ
- 各ユーザーストーリーは独立して完了・テスト可能
- チェックポイントで独立した検証を行う
- 避けるべき: 曖昧なタスク、同一ファイルへの競合、ストーリー間の依存関係
