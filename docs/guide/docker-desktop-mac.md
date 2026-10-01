# Docker Desktop への展開（Intel Mac）

Intel チップの MacBook に Docker Desktop を入れ、このワークベンチをローカルで動かす手順です。
所要時間は初回で 15〜30 分ほどです（大半はダウンロード待ち）。

!!! info "どのチップか確認する"
    メニューバーの  → **このMacについて** を開き、「プロセッサ」が **Intel** と表示されていればこの手順の対象です。
    「チップ: Apple M…」と表示される場合は、Docker Desktop のダウンロードで Apple Silicon 版を選ぶ点だけが異なります。

## 動作要件

| 項目 | 要件 |
|---|---|
| macOS | Docker Desktop が対応する版（最新とその前の 2 世代）。古い場合は先に macOS を更新する |
| メモリ | Mac 本体 8 GB 以上を推奨。Docker に 4 GB 以上を割り当てる |
| ディスク空き | 5 GB 以上（Docker Desktop 本体と 3 つのイメージで約 2〜3 GB） |
| 使うポート | 8000（ドキュメント）、8080（PlantUML）、8081（draw.io） |

使用している 3 つのイメージ（`plantuml/plantuml-server`、`jgraph/drawio`、`python:3.12-slim`）は、すべて Intel（amd64）向けのビルドが公開されています。

## 1. 開発ツールを入れる（git / make）

ターミナル（アプリケーション → ユーティリティ → ターミナル）を開き、次を実行します。

```bash
xcode-select --install
```

ダイアログが出たら **インストール** を押します。「already installed」と表示された場合はインストール済みなので、そのまま次へ進みます。

```bash
git --version   # git version 2.x と表示されれば OK
make --version  # GNU Make 3.81 などと表示されれば OK
```

## 2. Docker Desktop を入れる

1. [Docker Desktop のダウンロードページ](https://docs.docker.com/desktop/setup/install/mac-install/) を開き、**Docker Desktop for Mac with Intel chip** を選んで `.dmg` をダウンロードする。
2. `Docker.dmg` を開き、Docker のアイコンを **Applications** フォルダにドラッグする。
3. アプリケーションから **Docker** を起動し、利用規約に同意する。サインインはスキップしてかまいません。
4. メニューバーにクジラのアイコンが出て、Docker Desktop の画面左下が **Engine running** になれば起動完了です。

Homebrew を使っている場合は、`brew install --cask docker` でも入れられます（入れた後に一度 Docker を起動する）。

確認：

```bash
docker version          # Client と Server の両方に OS/Arch: linux/amd64 などが表示される
docker compose version  # Docker Compose version v2.x
```

### Docker Desktop の推奨設定

Docker Desktop の **Settings（歯車アイコン）** で次を確認します。

| 場所 | 設定 | 理由 |
|---|---|---|
| Resources → Advanced | Memory を **4 GB 以上** | PlantUML と draw.io が Java/ブラウザ系で、メモリが少ないと遅くなる |
| Resources → Advanced | CPU は 2〜4 | Intel Mac はファンが回りやすいので、上げすぎない |
| General | **Use Virtualization framework** をオン | 新しいファイル共有方式（VirtioFS）が使えるようになり、保存の反映が速い |
| General → Choose file sharing implementation | **VirtioFS** | 同上 |
| General | **Start Docker Desktop when you sign in** | 毎回自動で起動したい場合はオン |

変更したら **Apply & restart** を押します。

## 3. リポジトリを取得する

作業用フォルダ（ここではホームの `dev`）に clone します。

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/UeEmon/use-case-driven-development-workbench.git
cd use-case-driven-development-workbench
cp .env.example .env
```

!!! warning "iCloud 同期フォルダには置かない"
    「デスクトップ」「書類」を iCloud Drive で同期している場合、そこに置くとファイル監視が不安定になり、保存しても画面に反映されないことがあります。`~/dev` のような同期対象外のフォルダを使ってください。

## 4. 起動する

```bash
make up
```

初回はイメージのダウンロードとドキュメントサーバのビルドで数分かかります。
次のように表示されたら起動完了です。

```
docs     http://localhost:8000
plantuml http://localhost:8080
draw.io  http://localhost:8081
```

ブラウザで開いて確認します。

| URL | 表示されるもの |
|---|---|
| http://localhost:8000 | ワークベンチのサイト（図入りのユースケース） |
| http://localhost:8080 | PlantUML のエディタ画面 |
| http://localhost:8081 | draw.io の作図画面 |

Docker Desktop の **Containers** 画面には `use-case-driven-development-workbench` というグループの中に `ucdd-docs`・`ucdd-plantuml`・`ucdd-drawio` の 3 つが表示され、ここからも起動・停止・ログ確認ができます。

### 軽量モード（draw.io なし）

draw.io を使わない日は、ドキュメントと PlantUML だけを起動するとメモリと CPU を節約できます。

```bash
make up-lite
```

## 5. 日々の使い方

```bash
cd ~/dev/use-case-driven-development-workbench
make up        # 起動（Docker Desktop が起動していること）
make logs      # ドキュメントサーバのログを見る（Ctrl+C で抜ける）
make check     # ユースケースの整合性チェック
make down      # 停止
```

- `docs/` 配下の Markdown を保存すると、http://localhost:8000 が自動で再読み込みされます。
- エディタは何でもかまいません。[Visual Studio Code](https://code.visualstudio.com/) を使う場合は、拡張機能 **PlantUML**（jebbs）を入れ、設定の `plantuml.server` に `http://localhost:8080` を指定すると、エディタ内でも図のプレビューができます。
- Mac を再起動した後は、Docker Desktop を起動してから `make up` を実行します（`restart: unless-stopped` のため、Docker Desktop の起動だけで自動的に立ち上がることもあります）。

## 6. 更新とアンインストール

```bash
git pull                 # 最新の手順書・ユースケースを取得
make up                  # Dockerfile が変わっていれば自動で再ビルド
docker compose pull      # PlantUML・draw.io のイメージを最新にする（任意）
```

すべて消すときは次のとおりです。

```bash
docker compose down --rmi all   # コンテナとイメージを削除
```

Docker Desktop 自体は、画面右上の 🐞（Troubleshoot）→ **Uninstall** で削除できます。

## うまくいかないとき

| 症状 | 対処 |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop が起動していない。アプリを起動し、Engine running になるまで待つ |
| `port is already allocated` / `address already in use` | 他のアプリが同じポートを使っている。`lsof -i :8080` で確認し、`.env` の `PLANTUML_PORT=18080` のようにポートを変えて `make up` |
| `make: command not found` | 手順 1 の `xcode-select --install` を実行する |
| 保存しても localhost:8000 に反映されない | iCloud 同期フォルダに置いていないか確認。Settings で VirtioFS を選ぶ。`make down && make up` で再起動 |
| 図の部分がエラー表示になる | PlantUML の文法エラー。http://localhost:8080 に図のコードを貼ってエラー位置を確認する |
| 動作が重い・ファンが回り続ける | `make up-lite` で draw.io を止める。Docker の Memory を 4 GB 以上、CPU を 2〜4 にする |
| `no space left on device` | Docker Desktop の Troubleshoot → **Clean / Purge data**、または `docker system prune` で不要なイメージを削除 |
