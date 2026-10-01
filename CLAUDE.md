# CLAUDE.md

このリポジトリは、ICONIX 系のユースケース駆動開発を進めるためのワークベンチです。
成果物はすべて `docs/` 配下の Markdown と PlantUML で管理し、MkDocs で GitHub Pages
（https://ueemon.github.io/use-case-driven-development-workbench/）に公開します。

## 進め方（この順序を守る）

1. 要求: `docs/requirements/glossary.md`（用語）、`docs/requirements/actors.md`（アクター・ユースケース図）
2. ドメインモデル: `docs/domain/domain-model.md`（クラス図）
3. ユースケース記述: `docs/usecases/UC-xxx-<slug>.md`（基本コース・代替コース）
4. ロバストネス図: 同じファイル内。記述の各文を boundary / control / entity に対応させる
5. シーケンス図: 同じファイル内。control をクラスの操作に割り当て、ドメインモデルに反映する
6. 受け入れテスト: `tests/acceptance/UC-xxx.feature`（Feature に `@UC-xxx` タグ）

詳細は `docs/process.md` を参照。

## 書き方のルール

- ユースケース名は「〜する」で終わる動詞句。記述は能動態・現在形（「システムは〜を表示する」）。
- 画面名は「」で、ドメインオブジェクトは **太字** で書き、用語集とドメインモデルに必ず存在させる。
- ロバストネス図の接続は アクター↔boundary、boundary↔control、control↔entity、control↔control のみ。
- 各ユースケースの front matter（id, name, actor, status, issue, tests）を必ず埋める。
  status は `記述中 → 記述完了 → ロバストネス完了 → シーケンス完了 → 実装済` のいずれか。
- 図は PlantUML のコードブロック（```plantuml）で書く。画像ファイルは置かない。

## ユースケースを追加・変更したら

1. 新規はテンプレート `docs/guide/usecase-template.md` から作る（`make new ID=UC-003 SLUG=return-book`）
2. `mkdocs.yml` の nav と `docs/usecases/index.md` の一覧に追加
3. 新しい名詞を用語集・ドメインモデルに反映
4. `python scripts/check_usecases.py --write` を実行し、エラー 0 とトレーサビリティ表の更新を確認
5. ブランチ名は `uc/UC-xxx-<slug>`、PR 本文は `.github/pull_request_template.md` に沿って書き、`Refs UC-xxx` を含める

## コマンド

- `make up` / `make down`: Docker で docs(:8000)・PlantUML(:8080)・draw.io(:8081) を起動／停止
- `make check`: 整合性チェック（CI でも実行）
- `make build`: `mkdocs build --strict`
- Docker が使えない環境では `pip install -r requirements-docs.txt` 後に
  `python scripts/check_usecases.py` を直接実行する（PlantUML の描画には PlantUML Server が必要）

## 注意

- MkDocs は 1.x に固定（2.0 はプラグイン非互換）。`requirements-docs.txt` を勝手に上げない。
- `docs/templates/` という名前のフォルダは MkDocs が自動で除外するので使わない。
