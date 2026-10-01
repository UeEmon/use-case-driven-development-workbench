# Use Case Driven Development Workbench

ICONIX 系のユースケース駆動開発（ユースケース記述 → ロバストネス図 → シーケンス図 → ドメインモデル → 受け入れテスト）を、
**オープンソースだけ**・**Docker だけ**で回すためのリポジトリ雛形です。図はすべてテキスト（PlantUML）なので GitHub で差分レビューできます。

## 構成

| サービス | OSS | URL | 用途 |
|---|---|---|---|
| docs | [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) + [plantuml-markdown](https://github.com/mikitex70/plantuml-markdown) | http://localhost:8000 | ユースケース・モデルの閲覧（保存すると自動リロード） |
| plantuml | [PlantUML Server](https://github.com/plantuml/plantuml-server) | http://localhost:8080 | 図のレンダリング／ブラウザで試し描き |
| drawio | [draw.io](https://github.com/jgraph/docker-drawio) | http://localhost:8081 | 画面モック・自由形式の図 |

GitHub 側では Issue テンプレート（ユースケース）、PR チェックリスト、GitHub Actions（整合性チェック → ビルド → GitHub Pages 公開）を用意しています。

## はじめかた

```bash
git clone https://github.com/UeEmon/use-case-driven-development-workbench.git && cd use-case-driven-development-workbench
cp .env.example .env          # ポートを変える場合のみ編集
make up                       # = docker compose up -d --build
```

Mac への Docker Desktop の導入から説明した手順は [docs/guide/docker-desktop-mac.md](docs/guide/docker-desktop-mac.md)、外出先から自宅の Mac に接続する方法は [docs/guide/remote-access.md](docs/guide/remote-access.md) にあります。

http://localhost:8000 を開くとサンプル（図書館システムの UC-001 / UC-002）が表示されます。

`make` が使えない環境では `docker compose up -d --build` で起動し、チェックは
`docker compose run --rm --no-deps docs python scripts/check_usecases.py` で実行できます。

## 日々の作業

```bash
make new ID=UC-003 SLUG=return-book   # テンプレートからユースケースと .feature を作成
# → mkdocs.yml の nav に追加し、ブラウザで確認しながら書く
make check                            # ID重複・必須項目・状態と図の対応・テスト紐付けを検査
make trace                            # docs/traceability.md を更新
```

## ディレクトリ

```
docs/
  requirements/   用語集・アクター（ユースケース図）
  domain/         ドメインモデル（クラス図）
  usecases/       UC-xxx-*.md（記述＋ロバストネス図＋シーケンス図を1ファイルに）
  guide/          ユースケースのひな形
  traceability.md 自動生成：UC ↔ Issue ↔ 受け入れテスト
tests/acceptance/ UC-xxx.feature（Gherkin、@UC-xxx タグで紐付け）
scripts/          整合性チェック
.github/          Actions・Issue/PR テンプレート
docker/docs/      ドキュメントサーバのイメージ
```

## このテンプレートから新しいリポジトリを作る

1. GitHub の **Use this template → Create a new repository** で作成する。
2. 作成直後に `template-init` ワークフローが動き、README・`mkdocs.yml`・CLAUDE.md などの URL を新しいリポジトリ用に書き換えてコミットする（Actions タブで確認）。
3. 新しいリポジトリで **Settings → Pages → Source** を「GitHub Actions」にし、`docs` ワークフローを再実行する。
4. サンプル（UC-001 / UC-002、用語集、ドメインモデル）を自分の題材に置き換える。

## GitHub の初期設定

1. （設定済み）`mkdocs.yml` の `repo_url` はこのリポジトリを指しています。
2. **Settings → Pages → Source** を「GitHub Actions」にする（main へのマージで公開）。
3. **Settings → Branches** で main にブランチ保護を設定し、`docs / build` チェックを必須にする。
4. ラベル `usecase` を作成する（Issue テンプレートが使用）。
5. （任意）**Projects** でボードを作り、Issue の進捗チェックボックスと組み合わせてカンバン管理する。

## 受け入れテストの実行

`.feature` は実装言語に依存しない仕様として置いています。実装が始まったら、言語に合わせて
[behave](https://behave.readthedocs.io/)（Python）、[Cucumber](https://cucumber.io/)（Java/JS）、
[playwright-bdd](https://github.com/vitalets/playwright-bdd)（Web E2E）などで同じファイルを実行してください。
