Vision API Python Sandbox
===

Python 3.14 + Google Cloud Vision API のテキスト検出 (OCR) を試すサンドボックスです。

画像を選ぶと、Vision API の `TEXT_DETECTION` か `DOCUMENT_TEXT_DETECTION` でテキストを検出し、段落ごとのテキストと位置 (バウンディングボックス) を表示します。
段落のテキストは API が返す区切り情報 (空白・改行) で組み立てるので、日本語のように空白のない文章も単語ごとに分断されません。

## 構成

| 項目 | 内容 |
| --- | --- |
| 言語 | Python 3.14 (CI では 3.15 でも確認) |
| パッケージ管理 | [uv](https://docs.astral.sh/uv/) (`pyproject.toml` / `uv.lock`) |
| 主な依存 | google-cloud-vision 3.x, inquirer 3.x |
| Lint / 型 | ruff (lint + format), mypy (strict) |
| テスト | pytest + pytest-cov (Vision SDK はモック) |
| Docker | `python:3.14-slim` ベース、非 root 実行 (`Dockerfile` / `compose.yaml`) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| 依存更新 | Dependabot (uv・GitHub Actions・Docker を週 1 回) |

## クイックスタート

### Docker (おすすめ)

Docker と Docker Compose だけで動きます。

```bash
# lint・型チェック・テストをまとめて実行 (Vision API は呼ばない)
docker compose run --rm --build test

# 使い方を表示
docker compose run --rm --build app --help
```

Vision API を実際に呼ぶには、下の「下準備」で用意したサービスアカウント鍵をリポジトリ直下に置き、`.env` にパスを書きます。
API 呼び出しは課金対象です。

```bash
# .env
GOOGLE_APPLICATION_CREDENTIALS=./vision-api-python-sandbox-xxxx.json
```

```bash
# 画像とフィーチャーを指定して実行
docker compose run --rm app samples/synthetic-text.png --feature TEXT_DETECTION

# 引数を省くと images/ の画像とフィーチャーを対話で選ぶ
docker compose run --rm app
```

`app` はリポジトリを `/work` に読み取り専用でマウントし、`output/` だけ書き込めるようにしています。
画像・`.env`・鍵 JSON はイメージには入りません (`.dockerignore` は許可リスト方式)。
コンテナは既定で uid/gid 1000 で動きます。Linux で uid が異なる場合は、`output/` に書き込めるよう `HOST_UID` と `HOST_GID` を渡してください。

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose run --rm app samples/synthetic-text.png --feature TEXT_DETECTION
```

### ローカル (uv)

```bash
uv sync

uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy

uv run --env-file .env vision-sandbox samples/synthetic-text.png --feature TEXT_DETECTION
```

出力例 (合成画像 `samples/synthetic-text.png` の場合のイメージ):

```text
>>>> page 0 / block 0
    >>>> paragraph 0
         Hello, Vision API! (40, 50) (360, 50) (360, 95) (40, 95)
>>>> page 0 / block 1
    >>>> paragraph 0
         SAMPLE-2026 synthetic (40, 130) (470, 130) (470, 175) (40, 175)
output/annotate_image_response.json へ、もともとの JSON を書き出したよ。
```

### オプション

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `IMAGE` (位置引数) | なし (対話で選択) | 解析する画像ファイル |
| `--image-dir` | `images` | 対話選択で使う画像ディレクトリ |
| `--feature` | なし (対話で選択) | `TEXT_DETECTION` または `DOCUMENT_TEXT_DETECTION` |
| `--output` | `output/annotate_image_response.json` | API レスポンス全体の JSON の書き出し先 |
| `--timeout` | `60` | API 呼び出しのタイムアウト秒数 |

対象にする拡張子は `.png` `.jpg` `.jpeg` `.gif` `.bmp` `.webp` `.ico` `.tif` `.tiff` です。
レスポンス全体の JSON は、テキストが見つからなかったときも書き出します (前回の結果と取り違えないため)。
端末以外 (`docker compose run -T` やスクリプト) から実行するときは対話できないので、画像と `--feature` を引数で指定してください。
終了コードは、成功 (テキストなしを含む) が `0`、画像の読み込み・認証・API・JSON 書き出しのエラー、キャンセル、非対話環境での指定不足が `1`、引数の誤りが `2` です。

## 画像と個人情報

既存の画像は個人情報を含む可能性があるため、検証には合成画像を使用します。
合成画像のサンプルは `samples/synthetic-text.png` にあります (英字だけの架空テキスト)。
テストは Vision SDK のクライアントをモックするため、画像を外部に送りません。

OCR の結果は個人情報を含みうるため、`output/` は Git の管理対象外にしています。

## API の利用状況

API 全体の利用状況を確認できます。

https://console.cloud.google.com/apis/dashboard

Vision API の利用状況は次のページで確認できます。

https://console.cloud.google.com/apis/api/vision.googleapis.com/metrics

## 下準備

Cloud Vision API を使うには、Google Cloud のプロジェクトが必要です。
アカウントと請求先の用意は [Cloud Vision API を利用する準備](./Cloud%20Vision%20API%20を利用する準備.md) も参照してください。

1. https://console.cloud.google.com/welcome
2. 新しいプロジェクト
3. API とサービス > ライブラリ > Cloud Vision API を有効にする
4. API とサービス > 認証情報 > サービスアカウントを管理 > サービスアカウントを作成
    - サービスアカウントには Vision API の利用に必要な最小限の権限を設定します。
5. サービスアカウントを選択 > キー タブ > 鍵を追加 (JSON の鍵がダウンロードされる)
6. `.env` に登録
    - `GOOGLE_APPLICATION_CREDENTIALS=./vision-api-python-sandbox-....json`
    - 鍵の JSON は `.gitignore` の `*.json` でコミット対象外になります。

プロジェクトに請求先アカウントを関連付けます。

1. Google Cloud Console の「お支払い」> アカウントを作成
2. 請求先アカウントをプロジェクトに関連付けます。

## 使い終わったら

利用を終えたら、不要な呼び出しによる課金を避けるため Vision API を無効化してください。
