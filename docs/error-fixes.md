# Error Fix Case Studies (エラー修正事例集)

エラー修正時に参照する事例集。新しいエラーを修正したら、再発防止のためここに追記する。

---

## Template (テンプレート)

新しい事例を追加する際は、以下のフォーマットを使用：

```markdown
## [カテゴリ] 事例タイトル

**日付:** YYYY-MM-DD
**症状:** 何が起きたか
**原因:** なぜ起きたか
**解決策:** どう直したか

### Before
\`\`\`typescript
// 問題のあるコード
\`\`\`

### After
\`\`\`typescript
// 修正後のコード
\`\`\`

**教訓:** 今後気をつけること
**関連ファイル:** 影響を受けたファイルパス
```

---

## Categories (カテゴリ一覧)

- `[Svelte]` - Svelte/SvelteKit 関連
- `[TypeScript]` - 型定義、型エラー関連
- `[API]` - Backend/Frontend API 連携関連
- `[State]` - 状態管理関連
- `[Async]` - 非同期処理関連
- `[Import]` - インポート/モジュール関連
- `[Style]` - CSS/Tailwind 関連
- `[Tauri]` - Tauri デスクトップアプリ関連

---

## Case Studies (事例)

<!-- 新しい事例はここに追加 -->

### Example: [Svelte] Svelte 5 イベントハンドラ記法

**日付:** 2026-02-02
**症状:** ボタンクリックが反応しない
**原因:** Svelte 4 の `on:click` 記法を使用していた
**解決策:** Svelte 5 の `onclick` 記法に変更

### Before
```svelte
<button on:click={handleClick}>Click me</button>
```

### After
```svelte
<button onclick={handleClick}>Click me</button>
```

**教訓:** Svelte 5 ではイベントハンドラは `on:event` ではなく `onevent` 形式を使用
**関連ファイル:** すべての `.svelte` ファイル

---

### Example: [TypeScript] Optional プロパティ追加時の undefined エラー

**日付:** 2026-02-02
**症状:** `Cannot read property 'x' of undefined` エラー
**原因:** interface に optional プロパティを追加したが、使用箇所で undefined チェックをしていなかった
**解決策:** optional chaining (`?.`) またはデフォルト値を使用

### Before
```typescript
interface Config {
  settings?: { theme: string };
}

// 使用箇所
const theme = config.settings.theme; // Error!
```

### After
```typescript
// Option 1: Optional chaining
const theme = config.settings?.theme ?? 'default';

// Option 2: Default value
const theme = config.settings?.theme || 'default';
```

**教訓:** optional プロパティを追加したら、Grep でプロパティ名を検索し、すべての使用箇所で undefined 対策を確認
**関連ファイル:** 型定義を使用するすべてのファイル

---

### Example: [API] Pydantic モデルと TypeScript 型の不整合

**日付:** 2026-02-02
**症状:** フロントエンドでデータが表示されない、または型エラー
**原因:** Backend の Pydantic モデルを変更したが、Frontend の TypeScript 型を更新し忘れた
**解決策:** 両方の型定義を同期させる

### Before
```python
# backend/app/models.py
class CameraParams(BaseModel):
    x: float
    y: float
    z: float
    fov: float  # 新しく追加
```

```typescript
// frontend/src/lib/types.ts
interface CameraParams {
  x: number;
  y: number;
  z: number;
  // fov がない！
}
```

### After
```typescript
// frontend/src/lib/types.ts
interface CameraParams {
  x: number;
  y: number;
  z: number;
  fov: number;  // 追加
}
```

**教訓:** Backend のモデルを変更したら、必ず Frontend の対応する型も更新する。チェックリスト化する。
**関連ファイル:** `backend/app/models.py`, `frontend/src/lib/types.ts`

---

### Example: [Async] await 忘れによる Promise オブジェクト表示

**日付:** 2026-02-02
**症状:** 画面に `[object Promise]` と表示される、または期待したデータが表示されない
**原因:** async 関数の呼び出し時に `await` を忘れた
**解決策:** `await` を追加、または `.then()` でハンドリング

### Before
```typescript
const data = fetchData(); // Promise が返される
console.log(data); // [object Promise]
```

### After
```typescript
const data = await fetchData();
console.log(data); // 実際のデータ
```

**教訓:** async 関数を呼び出すときは必ず `await` をつける。IDE の型ヒントで `Promise<T>` になっていないか確認。
**関連ファイル:** async 関数を呼び出すすべてのファイル

---

### [State] プロジェクト読み込み時に bounds_wgs84 が欠落

**日付:** 2026-02-02
**症状:** カメラ設定画面で航空写真のオーバーレイが表示されない
**原因:** `.alproj`ファイルからプロジェクトを読み込む際、`_build_input_data`関数で`RasterFile`構築時に`bounds_wgs84`を渡していなかった
**解決策:** DSMとorthoの`RasterFile`構築時に`bounds_wgs84`を含めるように修正

### Before
```python
# backend/app/services/project_io.py
RasterFile(
    path=str(dsm_path),
    crs=dsm_info.get("crs"),
    resolution=dsm_info.get("resolution"),
    # bounds_wgs84 がない！
)
```

### After
```python
# backend/app/services/project_io.py
dsm_bounds = dsm_info.get("bounds_wgs84")
if dsm_bounds and isinstance(dsm_bounds, list):
    dsm_bounds = tuple(dsm_bounds)

RasterFile(
    path=str(dsm_path),
    crs=dsm_info.get("crs"),
    resolution=dsm_info.get("resolution"),
    bounds_wgs84=dsm_bounds,
)
```

**教訓:** シリアライズ/デシリアライズ時は、すべてのフィールドが正しく復元されるか確認する。特にオプショナルフィールドは見落としやすい。
**関連ファイル:** `backend/app/services/project_io.py`

---

### [API] 例外ハンドラ未登録による500エラー

**日付:** 2026-02-02
**症状:** カメラ推定で500エラーが発生、詳細なエラー情報が返されない
**原因:** `generic_exception_handler`がコメントアウトされており、`AppException`や`HTTPException`以外の例外がキャッチされなかった
**解決策:** 例外ハンドラを有効化

### Before
```python
# backend/app/api/deps.py
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    # app.add_exception_handler(Exception, generic_exception_handler)  # コメントアウト
```

### After
```python
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)  # 有効化
```

**教訓:** 開発中にデバッグ目的でコメントアウトしたコードは、本番環境では必ず有効化する。例外ハンドラがないと、詳細なエラー情報が失われ、デバッグが困難になる。
**関連ファイル:** `backend/app/api/deps.py`

---

### [TypeScript] 廃止した機能の残存（UFM削除漏れ）

**日付:** 2026-02-02
**症状:** マッチング画面で廃止したはずのUFMが選択肢として残っている
**原因:** 機能を廃止する際に、関連するすべてのファイルから参照を削除しなかった
**解決策:** Grepで廃止対象を検索し、すべての参照を削除

### 影響範囲チェックリスト
```bash
# 廃止する機能名で検索
grep -r "ufm" --include="*.ts" --include="*.svelte" --include="*.py"
```

### 削除が必要だった箇所（7ファイル）
- `frontend/src/lib/types/index.ts` - 型定義
- `frontend/src/routes/georectify/steps/processing/+page.svelte` - UI選択肢、ヘルパー関数
- `backend/app/schemas/georectify.py` - バリデーションpattern（2箇所）
- `backend/app/schemas/job.py` - バリデーションpattern
- `backend/app/api/routes/georectify.py` - ヘルパー関数
- `backend/app/services/georectify.py` - ヘルパー関数、エラーメッセージ
- `backend/app/api/deps.py` - エラー提案メッセージ

**教訓:** 機能を廃止する際は、必ずGrepで全ファイルを検索し、以下を確認する：
1. 型定義（TypeScript/Pydantic）
2. UI選択肢（ドロップダウン、ラジオボタン等）
3. バリデーションパターン（正規表現）
4. ヘルパー関数内の条件分岐
5. エラーメッセージや提案文字列

**関連ファイル:** 上記7ファイル

---

<!-- 今後のエラー修正事例をここに追加していく -->
