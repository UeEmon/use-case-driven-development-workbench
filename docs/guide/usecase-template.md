---
id: UC-XXX
name: （動詞で終わる名前：〜する）
actor: （主アクター）
status: 記述中
issue: （GitHub Issue 番号）
tests: tests/acceptance/UC-XXX.feature
---

# UC-XXX （ユースケース名）

このファイルをコピーして `docs/usecases/UC-XXX-英語名.md` として保存し、`mkdocs.yml` の nav に追加してください。

**主アクター**:　**事前条件**:　**事後条件**:

## 基本コース
1. （アクター）は「（画面名）」で〜する。
2. システムは **（ドメインオブジェクト）** を〜する。
3. システムは「（画面名）」に〜を表示する。

## 代替コース
- **2a. （条件）**: システムは〜する。

## ロバストネス図

```plantuml
@startuml
left to right direction
actor アクター
boundary 画面
control 処理
entity エンティティ
アクター --> 画面
画面 --> 処理
処理 --> エンティティ
@enduml
```

## シーケンス図

```plantuml
@startuml
actor アクター
boundary 画面
participant Controller
participant Entity
アクター -> 画面 : 操作
画面 -> Controller : method()
Controller -> Entity : method()
@enduml
```
