# リサーチ: オルソ化

**機能**: 001-georectification
**作成日**: 2025-01-27

## 技術選定

### 地図ライブラリ

**決定**: MapLibre GL JS

**理由**:
- オープンソース（BSD-3-Clause）でライセンス問題なし
- Mapbox GL JS のフォークで高性能
- ベクトルタイルとラスタタイル両対応
- カスタムレイヤー追加が容易（カメラ視野の扇形描画に必要）
- オフラインタイルキャッシュ可能
- Svelte との統合実績あり

**代替案検討**:
- Leaflet: 軽量だが3D対応が弱い、将来の Cesium.js 移行時に乖離が大きい
- OpenLayers: 機能豊富だが複雑、バンドルサイズ大
- Cesium.js: 3D地球儀だが初期MVPには過剰、将来的に追加検討

### Tauri サイドカー連携

**決定**: HTTP ローカルサーバー（FastAPI）

**理由**:
- Tauri の sidecar 機能で Python バイナリを同梱可能
- HTTP 通信は言語間連携が最もシンプル
- FastAPI の OpenAPI 自動生成でフロントエンド型生成が容易
- WebSocket で進捗通知可能

**代替案検討**:
- Tauri IPC + Rust から Python 呼び出し: Rust-Python 連携が複雑
- gRPC: オーバーヘッド、セットアップ複雑
- Unix ソケット: Windows 対応が面倒

**実装詳細**:
```
起動フロー:
1. Tauri 起動時に sidecar（Python バイナリ）を spawn
2. サイドカーは localhost:PORT で FastAPI サーバー起動
3. フロントエンドは http://localhost:PORT に API リクエスト
4. アプリ終了時にサイドカープロセスを kill
```

### ジョブキュー

**決定**: インメモリキュー + asyncio

**理由**:
- ローカルアプリなので Redis などの外部依存は不要
- 同時実行は1ジョブのみで十分
- asyncio.Queue で実装シンプル
- 進捗更新は WebSocket で push

**代替案検討**:
- Celery: 外部ブローカー必要、オーバースペック
- RQ: Redis 必要
- Dramatiq: 外部ブローカー必要

### プロジェクトファイル形式

**決定**: JSON（.alproj 拡張子）

**理由**:
- 人間が読める
- Python/TypeScript 両方で扱いやすい
- スキーマ検証可能（JSON Schema）
- バージョン管理しやすい

**代替案検討**:
- SQLite: 単一ファイルだがオーバースペック
- YAML: インデント問題、パース遅い
- Protocol Buffers: バイナリで人間が読めない

**スキーマバージョニング**:
```json
{
  "version": "1.0.0",
  "created_at": "2025-01-27T12:00:00Z",
  "updated_at": "2025-01-27T12:00:00Z",
  ...
}
```
- メジャーバージョン変更時は移行スクリプト提供
- マイナー/パッチは後方互換

### i18n ライブラリ

**決定**: svelte-i18n

**理由**:
- Svelte 公式推奨
- JSON 翻訳ファイル対応
- 遅延読み込み対応
- TypeScript 対応

**翻訳ファイル構造**:
```
frontend/src/lib/i18n/
├── index.ts       # 初期化
├── ja.json        # 日本語（デフォルト）
└── en.json        # 英語（将来）
```

## alproj 統合調査

### 進捗報告の実現方法

**課題**: alproj の CMAOptimizer は進捗コールバックを持たない

**解決策**:
1. CMAOptimizer の `optimize()` を世代ごとに分割呼び出し
2. 各世代終了時にフロントエンドに進捗を送信
3. または alproj をフォークして進捗コールバックを追加（将来）

**実装案**:
```python
async def run_optimization(params, progress_callback):
    optimizer = CMAOptimizer(...)
    for gen in range(max_generations):
        optimizer.step()  # 1世代分実行
        progress = (gen + 1) / max_generations
        await progress_callback(progress, optimizer.best_score)
        if cancelled:
            break
```

### キャンセル処理

**課題**: alproj の処理は同期的で中断困難

**解決策**:
1. 処理を別プロセスで実行（multiprocessing）
2. キャンセル時はプロセスを terminate
3. 部分結果は破棄（中間状態の保存は将来対応）

### メモリ使用量

**課題**: 大きな DSM/航空写真でメモリ不足

**解決策**:
1. rasterio の windowed reading で部分読み込み
2. 処理時は必要な範囲のみをメモリに展開
3. ユーザーに推奨 DSM 範囲を提示（対象画像の推定視野 + バッファ）

## UIデザイン調査

### ウィザードステップ

1. **データ入力**: DSM、航空写真、対象画像の選択
2. **カメラ設定**: 地図上でカメラ位置・方向・FoV を設定
3. **処理実行**: 自動最適化の実行と進捗表示
4. **結果確認**: 精度指標と補正画像のプレビュー
5. **エクスポート**: GeoTIFF 出力設定と保存

### 地図上のカメラ設定 UI

**インタラクション設計**:
- カメラ位置: 地図クリックでマーカー配置、ドラッグで移動
- 撮影方向: マーカーからドラッグで方向線を描画
- 視野角: 方向線の両端をドラッグで扇形の角度調整
- 標高: 数値入力（地図上では設定困難）

**視覚フィードバック**:
- 扇形で視野範囲を表示（半透明塗りつぶし）
- DSM/航空写真の範囲を矩形で表示
- カメラ位置に方向を示す矢印アイコン

## セキュリティ考慮

### ファイルアクセス

- ユーザーが明示的に選択したファイルのみアクセス
- Tauri の allowlist でファイルダイアログ経由のみ許可
- サイドカーはユーザーデータディレクトリのみ書き込み可

### ネットワーク

- 地図タイル取得のみ外部通信
- テレメトリなし
- 自動更新チェックはオプション（将来）

## 未解決事項

なし - すべての技術選定が完了

