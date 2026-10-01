# トレーサビリティ

ユースケース → GitHub Issue → 受け入れテストの対応表です。`make trace` で再生成されます（CI でも自動生成）。

<!-- TRACE:START -->
| ID | ユースケース | アクター | 状態 | Issue | 受け入れテスト |
|---|---|---|---|---|---|
| [UC-001](usecases/UC-001-search-books.md) | 書籍を検索する | 会員 | シーケンス完了 | [#1](https://github.com/UeEmon/use-case-driven-development-workbench/issues/1) | [UC-001.feature](https://github.com/UeEmon/use-case-driven-development-workbench/blob/main/tests/acceptance/UC-001.feature) |
| [UC-002](usecases/UC-002-lend-book.md) | 書籍を貸し出す | 司書 | ロバストネス完了 | [#2](https://github.com/UeEmon/use-case-driven-development-workbench/issues/2) | [UC-002.feature](https://github.com/UeEmon/use-case-driven-development-workbench/blob/main/tests/acceptance/UC-002.feature) |
<!-- TRACE:END -->
