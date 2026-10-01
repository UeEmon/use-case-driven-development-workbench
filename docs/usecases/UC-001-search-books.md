---
id: UC-001
name: 書籍を検索する
actor: 会員
status: シーケンス完了
issue: 1
tests: tests/acceptance/UC-001.feature
---

# UC-001 書籍を検索する

**主アクター**: 会員　**事前条件**: なし　**事後条件**: 検索結果が表示されている

## 基本コース
1. 会員は「検索画面」でキーワードを入力し、検索ボタンを押す。
2. システムはキーワードで **書籍** を検索する。
3. システムは該当した書籍の一覧と、各書籍の貸出可能な **蔵書** 数を「検索結果画面」に表示する。

## 代替コース
- **2a. キーワードが空**: システムは「検索画面」に「キーワードを入力してください」と表示する。
- **3a. 該当なし**: システムは「検索結果画面」に「該当する書籍はありません」と表示する。

## ロバストネス図

```plantuml
@startuml
left to right direction
skinparam shadowing false
actor 会員
boundary 検索画面
boundary 検索結果画面
control キーワードを検証する
control 書籍を検索する
control 貸出可能数を数える
entity BookCatalog
entity Book
entity Copy

会員 --> 検索画面
検索画面 --> キーワードを検証する
キーワードを検証する --> 検索画面 : 空の場合
キーワードを検証する --> 書籍を検索する
書籍を検索する --> BookCatalog
BookCatalog --> Book
書籍を検索する --> 貸出可能数を数える
貸出可能数を数える --> Copy
貸出可能数を数える --> 検索結果画面
@enduml
```

## シーケンス図

```plantuml
@startuml
skinparam shadowing false
actor 会員
boundary 検索画面
participant SearchController
participant BookCatalog
participant Book
participant Copy
boundary 検索結果画面

会員 -> 検索画面 : キーワード入力・検索
検索画面 -> SearchController : search(keyword)
alt keyword が空
  SearchController --> 検索画面 : エラー表示
else
  SearchController -> BookCatalog : search(keyword)
  BookCatalog --> SearchController : Book[]
  loop 各 Book
    SearchController -> Copy : isAvailable()
  end
  SearchController -> 検索結果画面 : show(books, availableCounts)
end
@enduml
```
