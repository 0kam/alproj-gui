# alproj_gui Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-27

## Active Technologies

- (001-georectification)

## Project Structure

```text
alproj_gui/
├── backend/           # FastAPI backend (Python 3.11, uv)
│   ├── app/           # Application code
│   └── .venv/         # Virtual environment
├── frontend/          # SvelteKit frontend (TypeScript, npm)
│   └── src/           # Source code
├── src-tauri/         # Tauri desktop app (Rust)
└── scripts/           # Development scripts
```

## Commands

### Development (Browser)

```bash
# Start both backend and frontend (recommended)
./scripts/dev.sh

# Or start separately:
# Backend (port 8765)
cd backend && uv run uvicorn app.main:app --reload --port 8765

# Frontend (port 5173)
cd frontend && npm run dev
```

**URLs:**
- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8765/docs

### Tauri Desktop App

```bash
# Development mode (hot reload)
cd src-tauri && cargo tauri dev

# Build release
cd src-tauri && cargo tauri build

# Build Python backend sidecar (required before release build)
./scripts/build-sidecar.sh
```

### Type Check & Lint

```bash
# Frontend
cd frontend && npm run check && npm run lint

# Backend
cd backend && uv run mypy . && uv run ruff check .
```

### Testing

```bash
# Backend
cd backend && uv run pytest

# Frontend (if tests exist)
cd frontend && npm run test
```

実際のデータを使ったテストが必要な場合は、
- devel_data/dsm.tif
- devel_data/airborne.tif
- devel_data/target_image.jpg

を使ってChromeでテストする。

## Code Style

: Follow standard conventions

## SpecKit Workflow Automation

When executing `/speckit.plan`, automatically continue through the entire workflow without waiting for user confirmation.

1. /speckit.plan to create plan. Then ssk codex about the plan.
2. /speckit.tasks to create tasks
3. /speckit.analyse to analyse spec, plan and tasks.
4. (if needed) re-run 1-3 until /speckit.analyse reports no issues (if reconsidering specify is required, wait for user confirmation)
5. run speckit.implement. 独立したタスクのまとまりを抽出し、SSAに並列で分担させて効率的な開発を行ってください。

### Automatic Workflow Sequence
```
/speckit.plan → /speckit.tasks → /speckit.implement
```

### Execution Rules
1. **After `/speckit.plan` completes** → Immediately execute `/speckit.tasks`
2. **After `/speckit.tasks` completes** → Immediately execute `/speckit.implement`
3. **During `/speckit.implement`** → Delegate to SSAs based on task types (see SSA Assignment Rules below)
4. **After all tasks complete** → Run validation (type check + tests)

### No User Confirmation Required
- Do NOT ask "Should I proceed?" between steps
- Do NOT wait for user approval between plan/tasks/implement
- Continue automatically until implementation is complete
- Only stop if critical errors occur that require user input

### SSA Delegation During Implementation
When executing `/speckit.implement`:
1. Parse `tasks.md` and categorize tasks by domain
2. Launch appropriate SSAs in parallel where possible
3. Coordinate SSA outputs and resolve conflicts
4. Run final validation after all SSAs complete

## SSA Implementation Strategy (speckit.implement)

When executing `/speckit.implement`, use SSAs (Subagents) for parallel implementation:

### SSA Assignment Rules
| Task Type | SSA (subagent_type) | Notes |
|-----------|---------------------|-------|
| Backend models/services | `backend-developer` | SQLAlchemy, FastAPI endpoints |
| Frontend components | `frontend-developer` | SvelteKit, Svelte 5, TanStack Query |
| API contracts/design | `api-designer` | OpenAPI specs, endpoint design |
| Test implementation | `test-automator` | pytest, vitest, integration tests |
| Database migrations | `backend-developer` | Alembic migrations |
| UI/UX components | `ui-designer` | Tailwind CSS, component styling |
| Full feature (small) | `fullstack-developer` | When frontend+backend tightly coupled |

### Execution Pattern
1. **Analyze tasks.md** - Group tasks by domain (backend/frontend/tests)
2. **Launch SSAs in parallel** - Use multiple Task tool calls in single message
3. **Coordinate results** - Main agent handles integration and conflicts
4. **Validate** - Run type checks and tests after each phase

### Parallel Execution Rules
- Tasks marked [P] in tasks.md → Launch SSAs in parallel
- Tasks affecting same files → Execute sequentially
- Backend and Frontend tasks → Can run in parallel
- Tests → Run after corresponding implementation

### Example: Parallel SSA Launch
```
// Launch backend and frontend SSAs simultaneously
Task(subagent_type="backend-developer", prompt="Implement User model and CRUD endpoints...")
Task(subagent_type="frontend-developer", prompt="Implement User list and form components...")
```

### Post-Implementation
After SSA completion:
1. Run `npm run check` (frontend) and `uv run mypy .` (backend)
2. Run tests: `uv run pytest` and `npm run test`
3. Review and fix any integration issues

## Active Technologies
- Python 3.11 (Backend), TypeScript 5.x (Frontend) + FastAPI, SQLAlchemy 2.0, Pydantic, SvelteKit, TanStack Query (001-administration)
- PostgreSQL with pgvector extension (001-administration)
- Python 3.11 (Backend), TypeScript 5.x (Frontend) + FastAPI, SQLAlchemy 2.0, Pydantic, SvelteKit, Svelte 5, TanStack Query, Tailwind CSS (001-administration)
- Python 3.11 (Backend), TypeScript 5.x (Frontend) + FastAPI, SQLAlchemy 2.0, Pydantic, SvelteKit, Svelte 5, TanStack Query, Tailwind CSS, h3-py, soundfile, numpy (002-data-management)
- PostgreSQL 16+ with pgvector extension (002-data-management)


## Recent Changes

- 001-georectification: Added

<!-- MANUAL ADDITIONS START -->

## Regression Prevention (回帰バグ防止)

コード修正時に過去の修正を壊さないための必須ルール。

**重要:** エラー修正時は `docs/error-fixes.md` の事例集を参照し、同様のパターンがないか確認すること。新しいエラーを修正したら、再発防止のため事例集に追記すること。

### 修正前の確認（MUST）

1. **関連コードの完全な把握**
   - 修正対象の関数/コンポーネントを呼び出しているすべての箇所を `Grep` で検索
   - 型定義（interface, type）が他でどう使われているか確認
   - 同じファイル内の他の関数との依存関係を確認

2. **既存テストの確認**
   - 修正対象に関連するテストを読み、期待される動作を理解
   - テストがない場合、既存の動作を壊さないよう特に注意

### 修正時の注意（MUST）

1. **インターフェース変更時**
   - 関数シグネチャを変更 → すべての呼び出し元を更新
   - props/パラメータを追加/削除 → すべての使用箇所を更新
   - 型定義を変更 → その型を使用するすべてのコードを更新

2. **状態管理の変更時**
   - store/state の構造変更 → すべての subscribe/読み取り箇所を確認
   - API レスポンス構造の変更 → フロントエンドの対応箇所を更新

3. **条件分岐の変更時**
   - 新しい条件を追加 → 既存のケースが影響を受けないか確認
   - else 節やデフォルト値の変更 → 意図しない副作用がないか確認

### 修正後の確認（MUST）

```bash
# 必ず型チェックを実行
cd frontend && npm run check
cd backend && uv run mypy .

# テストを実行
cd backend && uv run pytest
cd frontend && npm run test
```

### よくある失敗パターン

| パターン | 原因 | 対策 |
|---------|------|------|
| import エラー | ファイル移動/リネーム後の更新漏れ | Grep で旧パスを検索 |
| 型エラー | interface 変更後の対応漏れ | 型名で Grep して全使用箇所を確認 |
| undefined エラー | optional プロパティ追加時の未対応 | `?.` や デフォルト値の適用を確認 |
| 動作しない | 非同期処理の await 忘れ | async 関数呼び出し時は必ず await |
| データ不整合 | API と frontend の型不一致 | Pydantic モデルと TS 型を同期 |
| イベント未発火 | on:event → onevent の Svelte 5 変更忘れ | Svelte 5 では `onclick` 形式を使用 |

### SSA への指示

SSA（サブエージェント）にタスクを委譲する際は、以下を明示的に伝える：
- 変更対象ファイルの依存関係
- 既存のインターフェースで変更してはいけない部分
- 修正後に実行すべきチェックコマンド
- `docs/error-fixes.md` を参照して同様のエラーパターンを避けること

## Test Data

Development test data is located in `devel_data/`:

```
devel_data/
├── dsm.tif           # Digital Surface Model
├── airborne.tif      # Orthophoto (aerial image)
└── target_image.jpg  # Target mountain photo
```

### Initial Camera Parameters

```json
{
  "x": 732731, "y": 4051171, "z": 2458,
  "fov": 75, "pan": 95, "tilt": 0, "roll": 0,
  "a1": 1, "a2": 1,
  "k1": 0, "k2": 0, "k3": 0, "k4": 0, "k5": 0, "k6": 0,
  "p1": 0, "p2": 0,
  "s1": 0, "s2": 0, "s3": 0, "s4": 0,
  "w": 5616, "h": 3744, "cx": 2808, "cy": 1872
}
```

<!-- MANUAL ADDITIONS END -->
