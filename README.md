# Open ALO

**Write. Visualize. Run.**

## 日本語

Open ALOは、**ALOを書く → 機械検証する → 図で確認する → 判断を実行する**までを、特定サービスにロックインされず再現可能にするOSSプロジェクトです。

ALO（Abstract Language Object）は、判断を含む処理の流れを、入力・状態・判断・決定的なルール・出力として記述するテキスト形式です。判断だけをDecision Providerに任せ、算術・日付計算・状態更新・業務ルールはランタイム側で決定的に実行します。

## まず試す

最小サンプルは [`examples/minimal/`](examples/minimal/) にあります。

```text
examples/minimal/
├── alo.yaml    # ALO本体
├── input.json  # 実行時の入力例
└── README.md   # 期待するグラフと処理内容
```

`alo.yaml` は、サポート問い合わせを次のように振り分けます。

1. `message` を入力として受け取る
2. 緊急問い合わせかどうかを判断する（`binary`）
3. 技術・請求・その他のどれかを判断する（`categorical`）
4. 確率が閾値を超えた場合に、決定的なルールでアクションを決める
5. 判断が不確かな場合は人による確認に送る

## 使い方

Open ALOの基本的な流れは次のとおりです。

```text
ALOを書く
  ↓
alo validate    # 形式と必須項目を検証
  ↓
alo graph       # Graph IRからMermaid図を生成
  ↓
alo run         # 入力とDecision Providerで実行
  ↓
alo test        # 期待する結果をテスト
```

予定しているコマンドは次のとおりです。

```bash
# ALOの検証
alo validate examples/minimal/alo.yaml

# 判断グラフの生成
alo graph examples/minimal/alo.yaml

# 入力を指定して実行
alo run examples/minimal/alo.yaml --input examples/minimal/input.json

# サンプルやテストケースを実行
alo test examples/minimal/
```

現在は仕様と最小データが先行しており、CLI本体はまだ実装中です。上記コマンドは公開予定のインターフェースです。ALOの構造は [`schemas/alo.schema.json`](schemas/alo.schema.json) で検証でき、仕様の詳細は [`docs/spec.md`](docs/spec.md) を参照してください。

## ALOを書くときの基本

トップレベルには、少なくとも次の項目を記述します。

```yaml
alo:
  spec_version: "0.1"
  id: my-workflow
  version: "0.1.0"
  purpose: 判断処理の目的
  inputs: {}
  state_schema: {}
  decisions: []
  transition_rules: []
  outputs: {}
```

### 入力と状態

入力には型と必須かどうかを定義します。状態には型・初期値・更新担当を定義します。Decision Providerは状態を直接変更せず、状態更新はルールエンジンが担当します。

```yaml
inputs:
  message:
    type: string
    required: true

state_schema:
  status:
    type: enum
    values: [new, review, done]
    initial: new
    updated_by: rule_engine
```

### 判断

判断は3種類です。

| 型 | 用途 | Jevでの対応 |
| --- | --- | --- |
| `binary` | yes / no の判断 | Noul |
| `categorical` | 固定された選択肢から1つ選ぶ | Choice |
| `scalar` | 定義した尺度上のスコアを返す | Score |

`categorical` の選択肢はALOにあらかじめ宣言します。判断の確率やスコアを最終的なアクションに変換する処理は、`transition_rules` に決定的なルールとして記述します。

### Decision Provider

Decision Providerは判断を返す部品です。Jev、ローカルLLM、OpenAI互換API、テスト用のMockなどを利用できます。JevはOpen ALOそのものではなく、`binary / categorical / scalar` を実行するProviderの一実装です。

そのため、Jevがなくても次の処理は可能にします。

- ALOを読む
- スキーマを検証する
- Graph IRやMermaid図を生成する
- Mock Providerでテストする
- 決定的なルールを実行する

## リポジトリ内の主なファイル

```text
README.md                         # プロジェクト概要と使い方
docs/spec.md                     # ALO Draft 0.1の仕様
docs/architecture.md             # コンポーネント構成
schemas/alo.schema.json          # JSON Schema
examples/minimal/alo.yaml        # 最小のALO
examples/minimal/input.json      # 最小例への入力
ROADMAP.md                       # 実装ロードマップ
```

仕様変更や実装変更を行う場合は、ALOの可搬性、Decision Providerの状態非変更、決定的ルールと確率的判断の分離を維持してください。

---

## English

Open ALO is an open-source toolkit and specification for creating **Abstract Language Objects (ALO)**, visualizing them as explicit decision graphs, and executing them with **Jev or compatible decision providers**.

The goal:

> Anyone should be able to describe a decision workflow in language, inspect the resulting graph, run it reproducibly, fork it, and execute it locally without depending on a single vendor or hosted service.

## What Open ALO provides

```text
Natural-language intent
        ↓
      ALO
        ↓
 Validation / Compile
        ↓
    Graph IR
    ├── Mermaid diagram
    └── executable workflow
        ↓
Decision Provider
    ├── Jev
    ├── OpenAI-compatible models
    ├── local models
    └── mock/test provider
        ↓
Deterministic Rules
        ↓
 State transition / Output
```

Open ALO separates probabilistic judgment, deterministic computation, representation, visualization, and execution provider.

## Core principles

1. **Open specification** — ALO must be implementable without the reference runtime.
2. **Local-first** — hosted infrastructure must not be required.
3. **Provider-neutral** — Jev is supported, but ALO must not depend on Jev.
4. **Text-based artifacts** — ALO packages should remain readable, diffable, forkable, and Git-friendly.
5. **Graph as inspection surface** — diagrams are generated from the same source used for execution.
6. **Reproducibility** — inputs, versions, provider configuration, thresholds, rule traces, and outputs should be recordable.
7. **Testability** — decision nodes and deterministic rules are evaluated separately.
8. **No hidden state mutation** — providers return decisions; deterministic runtime code updates state.

## Decision model

| Open ALO type | Meaning | Jev mapping |
| --- | --- | --- |
| `binary` | yes/no probability | Noul |
| `categorical` | one option from a fixed set | Choice |
| `scalar` | degree or score on a defined scale | Score |

Jev is one **Decision Provider**, not the ALO specification itself.

## Repository layout

```text
open-alo/
├── README.md
├── docs/
│   ├── architecture.md
│   └── spec.md
├── schemas/
│   └── alo.schema.json
├── examples/
│   └── minimal/
│       ├── alo.yaml
│       └── README.md
├── packages/          # reference implementation (planned)
│   ├── core/
│   ├── compiler/
│   ├── runtime/
│   ├── cli/
│   └── providers/
├── conformance/       # compatibility tests (planned)
└── studio/            # visual editor / graph viewer (planned)
```

## Minimal ALO

```yaml
alo:
  spec_version: "0.1"
  id: support-triage
  version: "0.1.0"
  purpose: Route a customer support request.

  inputs:
    message:
      type: string
      required: true

  state_schema:
    status:
      type: enum
      values: [new, routed]
      initial: new
      updated_by: rule_engine

  decisions:
    - id: is_emergency
      type: binary
      reads: [input.message]
      question: Is this request an emergency?

    - id: category
      type: categorical
      reads: [input.message]
      options:
        technical: Technical problem
        billing: Billing problem
        other: Other

  transition_rules:
    - id: route-emergency
      when: decision.is_emergency.p_true >= 0.90
      set:
        action: escalate

  outputs:
    action:
      type: string
```

## Intended CLI

```bash
alo validate examples/minimal/alo.yaml
alo graph examples/minimal/alo.yaml
alo run examples/minimal/alo.yaml --input input.json
alo test examples/minimal/
```

The CLI does not exist yet. These commands define the intended public interface.

## Schema

The Draft 0.1 source schema is published at [`schemas/alo.schema.json`](schemas/alo.schema.json).
It is a JSON Schema for the parsed ALO data model, so YAML sources such as
`examples/minimal/alo.yaml` must be parsed as YAML before being validated against it.

## Jev

TypeSafe describes Jev as a model for typed probabilistic decisions inside software. Its published workflow examples decompose tasks into **Noul**, **Choice**, and **Score**, while keeping arithmetic, dates, and explicit rules in code.

Open ALO will support Jev through an adapter. A Jev account must never be required merely to read, validate, visualize, test, or run ALO with another provider.

- TypeSafe: https://typesafe.ai/
- Workflow examples: https://evals.typesafe.ai/

## Status

**Pre-alpha / specification-first.**

Current priorities:

1. Freeze the minimum ALO schema.
2. Define Graph IR.
3. Build schema validation.
4. Generate Mermaid deterministically.
5. Define the Decision Provider interface.
6. Add Jev and OpenAI-compatible adapters.
7. Implement the CLI.
8. Add conformance tests.
9. Build a self-hostable Studio.

## License

**TBD before the first tagged release.**

The project is intended to be openly usable, modifiable, redistributable, and self-hostable. The exact license will be selected explicitly rather than assumed.
