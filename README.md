# Open ALO

**Write ALO. See ALO. Calculate with Jev.**

> **Canonical semantics: Draft 0.2**
>
> Open ALO's core model is **`mainObj + subObjList + State + managerObj`**.
> Earlier Draft 0.1 documentation incorrectly reduced ALO to a probabilistic workflow DSL. See [Implementation Correction](docs/implementation-correction.md).

## ALOとは何か

ALO（Abstract Language Object）は、現実世界の概念・システム・役割・動的状態を、LLMが扱える**言語オブジェクト**として構造化する考え方です。

ALOの中核は4つです。

| 要素 | 役割 |
| --- | --- |
| `mainObj` | ALO全体を表す最上位オブジェクト |
| `subObjList` | mainObjを構成する子オブジェクト群 |
| `State` | ALOが保持する動的状態 |
| `managerObj` | 入力を解釈し、オブジェクトを協調させ、Stateを更新し、出力を作る実行主体 |

```text
ALOを書く
   ↓
ALO Prompt
   ↓
Canonical ALO Model
   ├────────────→ ALO図
   │
   └────────────→ managerObjを実行
                        │
             ┌──────────┼──────────┐
             │          │          │
           LLM      通常コード     Jev
                                   │
                        Noul / Choice / Score
                                   │
                                   ▼
                              managerObj
                                   │
                              State更新
                                   │
                                  出力
```

## 重要: JevはALOではない

Jevは、`managerObj` が必要とする曖昧な判断を計算するための**任意の実行手段**です。Jevの `Noul / Choice / Score` が `mainObj / subObjList / State / managerObj` を置き換えることはありません。

## ALO図

ALO図は、ALOの概念構造を可視化します。最低限、mainObj、subObjList、State、managerObj、Input、Outputの関係を表現し、必要に応じてJevや通常コードの計算ノードを重ねます。

## 最小ALO

正しい最小例は [examples/canonical-minimal/](examples/canonical-minimal/) にあります。

```yaml
alo:
  spec_version: "0.2"
  id: learning-coach
  version: "0.1.0"

  mainObj:
    id: learning_coach
    purpose: 学習者を支援する

  subObjList:
    - id: comprehension_analyzer
      purpose: 理解度を評価する
    - id: explanation_engine
      purpose: 状態に応じた説明を作る

  State:
    level: 1
    progress: 0.0
    activeStatus: initializing

  managerObj:
    input: user_message
    process:
      - 入力を読む
      - Stateを読む
      - 必要なsubObjを使う
      - 必要ならJevで意味判断を行う
      - 宣言された規則でStateを更新する
      - 出力を生成する
```

## 実装エージェント向け最短導線

**最初に読む:** [docs/complete-implementation-guide.md](docs/complete-implementation-guide.md)

この1ファイルだけで、ALOの定義、4要素、ALO Prompt、ALO図、Jevの位置づけ、Runtime、State更新、再現性、旧Draft 0.1の誤り、実装順、完了条件まで把握できるようにしています。

## 仕様を読む順番

1. [docs/spec.md](docs/spec.md) — **ALOそのもののNormative SSOT**
2. [docs/architecture.md](docs/architecture.md) — ALOをツールとして実装する構造
3. [docs/implementation-correction.md](docs/implementation-correction.md) — Draft 0.1からの修正内容
4. [examples/canonical-minimal/](examples/canonical-minimal/) — 最小の正しいALO
5. Jev / Graph / Runtimeの個別仕様

## 現在の実装について

旧Draft 0.1解釈（確率的ワークフローDSLとしてのALO）に基づくRuntime・Graph・スキーマ・サンプル・適合性フィクスチャは削除済みです（`docs/implementation-correction.md`参照）。Provider・CLI・パッケージングの各シェルは、Draft 0.1固有ではなかったため、そのままcanonicalモデル向けに再利用しています。Web UI（Studio）はユーザーが想定していなかったため削除しました——利用はコーディングエージェントがCLI（`alo validate/prompt/graph/run/test`）を直接使う形を前提とします。

コードが仕様と衝突する場合、`docs/spec.md` を優先し、コードを修正します。

## 目標

Open ALOは、誰でもALOを書き、プロンプトとして使い、図にし、managerObjの判断にJevを使い、実行を記録・再現し、ローカルで実行し、Fork・改変・共有できるOSSを目指します。

## Status

**Pre-alpha / semantic correction in progress.**

See [ROADMAP.md](ROADMAP.md).
