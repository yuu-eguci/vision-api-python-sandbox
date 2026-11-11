Vision API Python Sandbox
===

😎 Python 3.10 + Google Vision API

## How to Play?

こういう画像を用意しておいて……

既存の画像は個人情報を含む可能性があるため、検証には合成画像を使用します。
合成画像のサンプルは `samples/synthetic-text.png` にあります (英字だけの架空テキスト)。

```bash
# こんなふうに実行していく……
$ pipenv run python main.py

# こんなふうに、どの画像を使うか聞いてくれる……
[?] 選んでね: 難易度3のJavaScript早押しクイズ.png
 > 難易度3のJavaScript早押しクイズ.png
   色見本.png
   銀河鉄道の夜縦書き.png

# API の実呼び出しは検証で行いません。
# 出力例には合成データだけを使用します。
```

## API コールの履歴を見たい

ここにアクセスしようや。

https://console.cloud.google.com/apis/dashboard

API ごとに見たいときはこっちね。こっちっていうか上のとこ↑から潜れる。

https://console.cloud.google.com/apis/api/vision.googleapis.com/metrics

## 下準備が必要

Cloud Vision API を使うには、 Google Cloud Console で "プロジェクト" をいっこ作る必要がある。

**(MEMO for me) すでに自分用のプロジェクトは作ってあって、 Vision API は念のため無効化してある状態。**

1. https://console.cloud.google.com/welcome
2. 新しいプロジェクト
3. API とサービス > ライブラリ > Cloud Vision API を有効にする
4. API とサービス > 認証情報 > サービスアカウントを管理 > サービスアカウントを作成
    - Python から Vision API を使うだけなら、サービスアカウントは、 Vision API に対する最小限のアクセス権限だけを持てばよい
5. サービスアカウントをクリック > キータブ > 鍵を追加 > JSON が手に入る
6. .env 登録
    - `GOOGLE_APPLICATION_CREDENTIALS=./vision-api-python-sandbox-....json`

これで使えるかと思いきや、プロジェクトに対して請求アカウントをセットしておかないといけない。

1. Google Cloud のトップページみたいなとこから > 請求 > アカウントを作成
2. なんやかんやプロジェクトにそれを設定

## 遊び終わったら

Vision API を無効化しておこう。請求を回避するため。
