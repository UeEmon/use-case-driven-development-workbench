.DEFAULT_GOAL := help
-include .env
export
DC := docker compose
# Tailscale の CLI（PATH に無ければ Mac アプリ同梱のものを使う）
TAILSCALE := $(shell command -v tailscale 2>/dev/null || echo /Applications/Tailscale.app/Contents/MacOS/Tailscale)

help: ## コマンド一覧
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-16s %s\n", $$1, $$2}'

up: ## 環境を起動（docs:8000 / plantuml:8080 / drawio:8081）
	$(DC) up -d --build
	@echo "docs     http://localhost:$${DOCS_PORT:-8000}"
	@echo "plantuml http://localhost:$${PLANTUML_PORT:-8080}"
	@echo "draw.io  http://localhost:$${DRAWIO_PORT:-8081}"

up-lite: ## draw.io なしで起動（docs:8000 / plantuml:8080）
	$(DC) up -d --build docs plantuml
	@echo "docs     http://localhost:$${DOCS_PORT:-8000}"
	@echo "plantuml http://localhost:$${PLANTUML_PORT:-8080}"

down: ## 環境を停止（トンネルも含む）
	$(DC) --profile tunnel down

cloudflare-setup: ## Cloudflare Tunnel + Access を自動設定（ARGS=--delete で削除）
	$(DC) run --rm --no-deps -e CLOUDFLARE_API_TOKEN docs python scripts/cloudflare_setup.py $(ARGS)

tunnel: ## Cloudflare Tunnel を起動（先に make cloudflare-setup）
	@test -n "$(CLOUDFLARE_TUNNEL_TOKEN)" || (echo ".env に CLOUDFLARE_TUNNEL_TOKEN がありません。先に make cloudflare-setup を実行してください" && exit 1)
	$(DC) --profile tunnel up -d --build
	@echo "公開先: https://$${CLOUDFLARE_HOSTNAME:-（Cloudflare で設定したホスト名）}"
	@echo "接続状態: docker compose logs -f cloudflared"

remote: ## Tailscale Serve で docs を tailnet に HTTPS 公開（Tailscale が必要）
	$(TAILSCALE) serve --https=443 --bg localhost:$${DOCS_PORT:-8000}
	$(TAILSCALE) serve status

remote-all: ## Tailscale Serve で docs / plantuml / draw.io をすべて公開
	$(TAILSCALE) serve --https=443 --bg localhost:$${DOCS_PORT:-8000}
	$(TAILSCALE) serve --https=8443 --bg localhost:$${PLANTUML_PORT:-8080}
	$(TAILSCALE) serve --https=10000 --bg localhost:$${DRAWIO_PORT:-8081}
	$(TAILSCALE) serve status

remote-off: ## Tailscale Serve の公開をすべて止める
	$(TAILSCALE) serve reset

logs: ## ログを表示
	$(DC) logs -f docs

check: ## ユースケースの整合性チェック
	$(DC) run --rm --no-deps docs python scripts/check_usecases.py

trace: ## トレーサビリティ表を更新
	$(DC) run --rm --no-deps docs python scripts/check_usecases.py --write

build: ## 静的サイトを site/ に出力
	$(DC) run --rm docs mkdocs build --strict

new: ## 新しいユースケースを作成（例: make new ID=UC-003 SLUG=return-book）
	@test -n "$(ID)" -a -n "$(SLUG)" || (echo "usage: make new ID=UC-003 SLUG=return-book" && exit 1)
	sed 's/UC-XXX/$(ID)/g' docs/guide/usecase-template.md | grep -v 'このファイルをコピーして' > docs/usecases/$(ID)-$(SLUG).md
	printf '@$(ID)\nFeature: $(ID)\n' > tests/acceptance/$(ID).feature
	@echo "作成しました。mkdocs.yml の nav に docs/usecases/$(ID)-$(SLUG).md を追加してください"

.PHONY: help up up-lite down cloudflare-setup tunnel remote remote-all remote-off logs check trace build new
