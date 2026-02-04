# データモデル: オルソ化

**機能**: 001-georectification
**作成日**: 2025-01-27

## エンティティ一覧

```
┌─────────────────┐       ┌─────────────────┐
│    Project      │───────│   InputData     │
└─────────────────┘       └─────────────────┘
        │                         │
        │                         ├── DSM
        │                         ├── Ortho (航空写真)
        │                         └── TargetImage
        │
        ├─────────────────────────┐
        │                         │
        ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│ CameraParams    │       │  ProcessResult  │
└─────────────────┘       └─────────────────┘
        │                         │
        │                         ├── GCPList
        │                         ├── Metrics
        │                         └── GeoTIFF
        │
        ▼
┌─────────────────┐
│      GCP        │
└─────────────────┘
```

## エンティティ詳細

### Project

オルソ化作業の単位。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| id | string (UUID) | ✓ | 一意識別子 |
| version | string | ✓ | スキーマバージョン（例: "1.0.0"） |
| name | string | ✓ | プロジェクト名 |
| created_at | datetime (UTC) | ✓ | 作成日時 |
| updated_at | datetime (UTC) | ✓ | 更新日時 |
| input_data | InputData | ✓ | 入力データ |
| camera_params | CameraParams | | カメラパラメータ（初期値 + 最適化後） |
| camera_simulation | string | | カメラ設定のシミュレーション画像プレビュー（data URL/base64） |
| process_result | ProcessResult | | 処理結果 |
| status | enum | ✓ | draft / processing / completed / error |

**状態遷移**:
```
draft ──(処理開始)──> processing ──(成功)──> completed
                          │
                          └──(失敗)──> error
```

### InputData

入力データセット。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| dsm | RasterFile | ✓ | 数値表層モデル |
| ortho | RasterFile | ✓ | 航空写真/オルソ画像 |
| target_image | ImageFile | ✓ | 対象の景観写真 |

### RasterFile

GeoTIFF ファイルの参照。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| path | string | ✓ | ファイルパス |
| crs | string | ✓ | 座標参照系（EPSG コード） |
| bounds | BoundingBox | ✓ | 範囲（xmin, ymin, xmax, ymax） |
| resolution | [float, float] | ✓ | 解像度（x, y） |
| size | [int, int] | ✓ | ピクセルサイズ（width, height） |

### ImageFile

対象画像ファイルの参照。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| path | string | ✓ | ファイルパス |
| size | [int, int] | ✓ | ピクセルサイズ（width, height） |
| exif | ExifData | | EXIF メタデータ |

### ExifData

EXIF から抽出した情報。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| datetime | datetime | | 撮影日時 |
| gps_lat | float | | GPS 緯度 |
| gps_lon | float | | GPS 経度 |
| gps_alt | float | | GPS 標高 |
| focal_length | float | | 焦点距離 (mm) |
| camera_model | string | | カメラ機種 |

### CameraParams

カメラパラメータ。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| initial | CameraParamsValues | ✓ | 初期値（ユーザー入力） |
| optimized | CameraParamsValues | | 最適化後の値 |

### CameraParamsValues

カメラパラメータの値。

| フィールド | 型 | 必須 | 説明 | 単位 |
|-----------|------|------|------|------|
| x | float | ✓ | カメラ位置 X | m（CRS単位） |
| y | float | ✓ | カメラ位置 Y | m（CRS単位） |
| z | float | ✓ | カメラ位置 Z（標高） | m |
| fov | float | ✓ | 視野角 | 度 |
| pan | float | ✓ | パン角（方位） | 度（北=0, 東=90） |
| tilt | float | ✓ | チルト角 | 度（0=水平） |
| roll | float | ✓ | ロール角 | 度 |
| a1 | float | | 歪み係数 | - |
| a2 | float | | 歪み係数 | - |
| k1-k6 | float | | 放射歪み係数 | - |
| p1, p2 | float | | 接線歪み係数 | - |
| s1-s4 | float | | 薄プリズム歪み係数 | - |
| cx | float | | 主点 X | ピクセル |
| cy | float | | 主点 Y | ピクセル |

### ProcessResult

処理結果。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| gcps | GCP[] | ✓ | 検出された GCP リスト |
| metrics | ProcessMetrics | ✓ | 精度指標 |
| geotiff_path | string | | 出力 GeoTIFF パス |
| log | string[] | | 処理ログ |

### GCP

地上基準点。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| id | int | ✓ | 識別子 |
| image_x | float | ✓ | 画像座標 X | ピクセル |
| image_y | float | ✓ | 画像座標 Y | ピクセル |
| geo_x | float | ✓ | 地理座標 X | m（CRS単位） |
| geo_y | float | ✓ | 地理座標 Y | m（CRS単位） |
| geo_z | float | ✓ | 地理座標 Z（標高） | m |
| residual | float | | 残差 | ピクセル |
| enabled | bool | ✓ | 有効フラグ |

### ProcessMetrics

精度指標。

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| rmse | float | ✓ | 二乗平均平方根誤差 |
| gcp_count | int | ✓ | 使用 GCP 数 |
| gcp_total | int | ✓ | 検出 GCP 総数 |
| residual_mean | float | ✓ | 残差平均 |
| residual_std | float | ✓ | 残差標準偏差 |
| residual_max | float | ✓ | 残差最大値 |

## バリデーションルール

### Project

- `name`: 1-255文字
- `status`: 有効な enum 値のみ
- `version`: セマンティックバージョニング形式

### InputData

- すべてのファイルパスは存在すること
- DSM と Ortho の CRS が一致すること（警告のみ、変換可能）
- DSM と Ortho の範囲が重複すること

### CameraParamsValues

- `x`, `y`: DSM/Ortho の範囲内
- `z`: 0 以上
- `fov`: 1-180 度
- `pan`: 0-360 度
- `tilt`: -90-90 度
- `roll`: -180-180 度

### GCP

- `image_x`, `image_y`: 画像範囲内
- `enabled`: デフォルト true

## プロジェクトファイル形式

拡張子: `.alproj`
形式: JSON

```json
{
  "version": "1.0.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Mountain Photo",
  "created_at": "2025-01-27T03:00:00Z",
  "updated_at": "2025-01-27T03:30:00Z",
  "status": "completed",
  "input_data": {
    "dsm": {
      "path": "/path/to/dsm.tif",
      "crs": "EPSG:6690",
      "bounds": [732000, 4050000, 734000, 4052000],
      "resolution": [1.0, 1.0],
      "size": [2000, 2000]
    },
    "ortho": { ... },
    "target_image": { ... }
  },
  "camera_params": {
    "initial": {
      "x": 732731, "y": 4051171, "z": 2458,
      "fov": 75, "pan": 95, "tilt": 0, "roll": 0,
      ...
    },
    "optimized": { ... }
  },
  "process_result": {
    "gcps": [ ... ],
    "metrics": { ... },
    "geotiff_path": "/path/to/output.tif"
  }
}
```

## マイグレーション戦略

### バージョン 1.0.0 → 1.1.0（例）

- 新規フィールド追加: デフォルト値で補完
- フィールド削除: 無視（後方互換）
- フィールド名変更: マイグレーション関数で変換

```python
def migrate_1_0_to_1_1(data: dict) -> dict:
    # 例: フィールド名変更
    if "old_field" in data:
        data["new_field"] = data.pop("old_field")
    # 例: 新規フィールド追加
    data.setdefault("new_optional_field", None)
    data["version"] = "1.1.0"
    return data
```
