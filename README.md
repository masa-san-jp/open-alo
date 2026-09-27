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
    level:
      type: integer
      value: 1
    progress:
      type: number
      value: 0.0
    activeStatus:
      type: string
      value: initializing

  managerObj:
    id: learning_coach_manager
    input:
      - user_message
    process:
      - id: read_input
        action: 入力とStateを読む
      - id: analyze
        action: comprehension_analyzerで理解度を評価する
        calculation:
          provider: optional
          jev:
            type: Noul
            question: 学習者は対象概念を実質的に理解しているか
      - id: respond
        action: explanation_engineで状態に応じた応答を作る
    output:
      - response
```

（このYAMLはそのまま `alo validate` を通ります。実行方法は次のセクション参照。）

## インストールと実行

```bash
git clone https://github.com/masa-san-jp/open-alo.git
cd open-alo
```

Python 3.10以上が必要です。標準ライブラリのみで動作し、追加の`pip install`は必須ではありません（YAML入力を使う場合のみ、`pip install pyyaml`を推奨——未インストールでもRubyがあればそちらでYAMLを解析します。JSON入力なら追加要件なしで動きます）。

まだパッケージ化されていないため、`alo`コマンドは`python3 -m packages.cli`経由で呼び出します。

```bash
python3 -m packages.cli validate examples/canonical-minimal/alo.yaml
python3 -m packages.cli prompt   examples/canonical-minimal/alo.yaml
python3 -m packages.cli graph    examples/canonical-minimal/alo.yaml
python3 -m packages.cli test     examples/canonical-minimal
```

テストスイート全体は次で実行できます。

```bash
python3 -m unittest discover -s tests
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

## Contributing

貢献方法は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## License

[MIT](LICENSE)

## Status

**Pre-alpha / semantic correction in progress.**

See [ROADMAP.md](ROADMAP.md).
