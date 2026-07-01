# W杯2026 TV放送チェッカー（スクレイピング版）

Goal.com からW杯2026のTV放送スケジュールを自動取得し、ブラウザで快適に確認できるWebアプリです。

---

## ファイル構成

```
スクレイピング W杯2026TV放送チェッカー/
├── scraper.py     ← Goal.comをスクレイピングして matches.json を生成
├── matches.json   ← 試合データ（scraper.py が上書き更新）
├── index.html     ← ブラウザで表示するW杯放送チェッカー本体
└── README.md      ← このファイル
```

---

## scraper.py の実行方法

### 必要なもの

```bash
pip install requests beautifulsoup4
```

Goal.com が JavaScript レンダリングを必要とする場合は Selenium も必要です：

```bash
pip install selenium
```

Selenium を使う場合は **ChromeDriver** も必要です。
- Chrome のバージョンに合ったものを https://chromedriver.chromium.org/ からダウンロード
- または `pip install webdriver-manager` でも取得できます

### 実行コマンド

```bash
# scraper.py があるフォルダで実行
cd "スクレイピング W杯2026TV放送チェッカー"
python scraper.py
```

実行後のコンソール出力例：
```
==================================================
W杯2026 TV放送スケジュール スクレイパー
==================================================

スクレイピング対象:
  https://www.goal.com/jp/リスト/2026-world-cup-all-tv-guide/blt70f25e7f12788cd5

【ステップ1】requestsでページ取得を試みます...
  ✅ 取得成功 (タイトル: ...)
【ステップ3】試合データを解析中...
【ステップ4】matches.json に保存中...

==================================================
✅ 104試合のデータを取得しました
  日本戦: 3試合
  地上波放送あり: 50試合
  期間: 6/12 〜 7/20
==================================================
```

### スクレイピングに失敗した場合

Goal.com のHTML構造が変わった場合は、`scraper.py` 内の `parse_matches_from_soup()` 関数を  
実際のHTML構造に合わせて修正してください。

ページの構造確認コマンド：
```bash
python -c "
import requests
r = requests.get(
    'https://www.goal.com/jp/リスト/2026-world-cup-all-tv-guide/blt70f25e7f12788cd5',
    headers={'User-Agent': 'Mozilla/5.0'}
)
print(r.text[:5000])
"
```

---

## matches.json の手動編集方法

スクレイピングで取得できなかった情報（放送局の追加・修正など）は `matches.json` を直接編集して補完できます。

### フォーマット

```json
[
  {
    "date": "6/15",
    "time": "05:00",
    "stage": "F組1節",
    "team1": "オランダ",
    "team2": "日本",
    "tv_onair": ["NHK"],
    "tv_bs": [],
    "tv_net": [],
    "is_japan": true
  }
]
```

### 各フィールドの説明

| フィールド | 型 | 説明 | 例 |
|---|---|---|---|
| `date` | string | 日付（日本時間） | `"6/15"` |
| `time` | string | キックオフ時刻（日本時間） | `"05:00"` |
| `stage` | string | ステージ名 | `"F組1節"`, `"ラウンド32"`, `"決勝"` |
| `team1` | string | チーム名（日本語） | `"日本"`, `"未定"` |
| `team2` | string | チーム名（日本語） | `"ブラジル"`, `"未定"` |
| `tv_onair` | array | 地上波放送局 | `["NHK"]`, `["日テレ", "NHK"]`, `[]` |
| `tv_bs` | array | BS放送局 | `["NHK BS"]`, `[]` |
| `tv_net` | array | ネット配信サービス | `["DAZN"]`, `["ABEMA"]`, `[]` |
| `is_japan` | boolean | 日本代表戦かどうか | `true` / `false` |
| `note` | string | 補足説明（任意） | `"A組2位 vs B組2位"` |

### 放送局名の統一表記

| 放送局 | `tv_onair` に記載する値 |
|---|---|
| NHK総合 | `"NHK"` |
| 日本テレビ | `"日テレ"` |
| フジテレビ | `"フジテレビ"` |
| テレビ朝日 | `"テレビ朝日"` |
| TBS | `"TBS"` |

| 放送局 | `tv_bs` に記載する値 |
|---|---|
| NHK BS / BSP4K | `"NHK BS"` |

| サービス | `tv_net` に記載する値 |
|---|---|
| DAZN | `"DAZN"` |
| ABEMA | `"ABEMA"` |

---

## ブラウザでの確認方法（ローカル）

`index.html` をブラウザで直接開くと `fetch` がブロックされる場合があります。  
その場合は簡易サーバーを起動してください：

```bash
# Python 3
python -m http.server 8080
# → http://localhost:8080 をブラウザで開く
```

または VS Code の **Live Server** 拡張機能を使うと便利です。

---

## Netlify へのデプロイ手順

`index.html` と `matches.json` の2ファイルをアップロードするだけで公開できます。

### 方法1：ドラッグ＆ドロップ（最も簡単）

1. [Netlify Drop](https://app.netlify.com/drop) を開く
2. このフォルダ（`スクレイピング W杯2026TV放送チェッカー/`）ごとドラッグ＆ドロップ
3. 自動でデプロイされ、URLが発行される

### 方法2：Netlify CLI

```bash
npm install -g netlify-cli
netlify deploy --dir . --prod
```

### 放送情報を更新するには

1. `python scraper.py` を実行して `matches.json` を最新化
2. 更新した `matches.json` を Netlify に再アップロード（ドラッグ＆ドロップで上書き可）

---

## 機能一覧

| 機能 | 説明 |
|---|---|
| 日付フィルター | ◀▶ボタンで1日ずつ切り替え、「今日」ボタンで当日にジャンプ |
| 日本戦フィルター | 日本代表戦のみ表示 |
| 地上波フィルター | 地上波放送がある試合のみ表示 |
| BS/DAZNフィルター | BSまたはネット配信がある試合のみ表示 |
| LIVE表示 | 試合開始〜120分間は「LIVE」バッジをアニメーション表示 |
| 日本戦カウントダウン | 次の日本戦まであと何時間かをリアルタイムカウントダウン |
| ライト/ダークテーマ | ヘッダー右のボタンで切替（設定はブラウザに保存） |
| 国旗表示 | [flagcdn.com](https://flagcdn.com) から各国の国旗を取得 |

---

## 注意事項

- 放送情報は変更される場合があります。最新情報は各放送局の公式サイトをご確認ください。
- Goal.com の利用規約に従ってご利用ください。スクレイピングは適度な間隔で実施してください。
- JavaScript が無効な環境（Goal.com がSPAの場合）では `scraper.py` の Selenium モードをご利用ください。
