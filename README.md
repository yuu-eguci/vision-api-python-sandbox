Vision API Python Sandbox
===

😎 Python 3.14 + Google Cloud Vision API のテキスト検出 (OCR) を試すサンドボックス

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
**API 呼び出しは課金対象です。**

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
終了コードは、成功 (テキストなしを含む) が `0`、画像の読み込み・認証・API・JSON 書き出しのエラーやキャンセルが `1`、引数の誤りが `2` です。

## 画像と個人情報

既存の画像は個人情報を含む可能性があるため、検証には合成画像を使用します。
合成画像のサンプルは `samples/synthetic-text.png` にあります (英字だけの架空テキスト)。
テストは Vision SDK のクライアントをモックするため、画像を外部に送りません。

OCR の結果は個人情報を含みうるため、`output/` は Git の管理対象外にしています。

## API コールの履歴を見たい

ここにアクセスしようや。

https://console.cloud.google.com/apis/dashboard

API ごとに見たいときはこっちね。こっちっていうか上のとこ↑から潜れる。

https://console.cloud.google.com/apis/api/vision.googleapis.com/metrics

## 下準備が必要

Cloud Vision API を使うには、 Google Cloud Console で "プロジェクト" をいっこ作る必要がある。
アカウントと請求先の用意は [Cloud Vision API を利用する準備](./Cloud%20Vision%20API%20を利用する準備.md) も参照。

**(MEMO for me) すでに自分用のプロジェクトは作ってあって、 Vision API は念のため無効化してある状態。**

1. https://console.cloud.google.com/welcome
2. 新しいプロジェクト
3. API とサービス > ライブラリ > Cloud Vision API を有効にする
4. API とサービス > 認証情報 > サービスアカウントを管理 > サービスアカウントを作成
    - Python から Vision API を使うだけなら、サービスアカウントは、 Vision API に対する最小限のアクセス権限だけを持てばよい
5. サービスアカウントをクリック > キータブ > 鍵を追加 > JSON が手に入る
6. .env 登録
    - `GOOGLE_APPLICATION_CREDENTIALS=./vision-api-python-sandbox-....json`
    - 鍵の JSON は `.gitignore` の `*.json` でコミット対象外になっている

これで使えるかと思いきや、プロジェクトに対して請求アカウントをセットしておかないといけない。

1. Google Cloud のトップページみたいなとこから > 請求 > アカウントを作成
2. なんやかんやプロジェクトにそれを設定

## 遊び終わったら

Vision API を無効化しておこう。請求を回避するため。
