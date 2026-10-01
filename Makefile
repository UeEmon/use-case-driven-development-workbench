.DEFAULT_GOAL := help
DC := docker compose

help: ## コマンド一覧
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-8s %s\n", $$1, $$2}'

up: ## 環境を起動（docs:8000 / plantuml:8080 / drawio:8081）
	$(DC) up -d --build
	@echo "docs     http://localhost:$${DOCS_PORT:-8000}"
	@echo "plantuml http://localhost:$${PLANTUML_PORT:-8080}"
	@echo "draw.io  http://localhost:$${DRAWIO_PORT:-8081}"

down: ## 環境を停止
	$(DC) down

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

.PHONY: help up down logs check trace build new
