#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W杯2026 TV放送スケジュール スクレイパー
Goal.com からW杯2026のTV放送情報をスクレイピングして matches.json を生成します。
"""

import json
import sys
import re
import os
from datetime import datetime

# スクレイピング対象URL（TV放送情報）
URL = "https://www.goal.com/jp/リスト/2026-world-cup-all-tv-guide/blt70f25e7f12788cd5"

# 試合結果・スコア取得URL
RESULTS_URL = "https://www.goal.com/jp/リスト/fifa-world-cup-2026-match-schedule/bltcbcc3591b503b5cf"

# 出力ファイル
OUTPUT_FILE    = os.path.join(os.path.dirname(__file__), "matches.json")
INDEX_HTML     = os.path.join(os.path.dirname(__file__), "index.html")

# 放送局名の正規化マッピング（Goal.comの表記 → 統一表記）
BROADCASTER_MAP = {
    "NHK": "NHK",
    "NHK総合": "NHK",
    "NHK Eテレ": "NHK",
    "NHK E テレ": "NHK",
    "NHK BS": "NHK BS",
    "NHK BS1": "NHK BS",
    "NHK BS4K": "NHK BS",
    "BSP4K": "NHK BS",
    "日本テレビ": "日テレ",
    "日テレ": "日テレ",
    "日テレ系": "日テレ",
    "フジテレビ": "フジテレビ",
    "フジ": "フジテレビ",
    "テレビ朝日": "テレビ朝日",
    "テレ朝": "テレビ朝日",
    "TBS": "TBS",
    "DAZN": "DAZN",
    "テレビ東京": "テレビ東京",
    "テレ東": "テレビ東京",
    "ABEMA": "ABEMA",
}

# 地上波放送局のセット
TERRESTRIAL_BROADCASTERS = {"NHK", "日テレ", "フジテレビ", "テレビ朝日", "TBS", "テレビ東京"}

# BS放送局のセット
BS_BROADCASTERS = {"NHK BS"}

# ネット配信のセット
NET_BROADCASTERS = {"DAZN", "ABEMA"}

# 日本語チーム名判定（日本戦の検出に使用）
JAPAN_NAMES = {"日本", "サムライブルー", "日本代表"}


def normalize_broadcaster(name: str) -> str:
    """放送局名を統一表記に変換する"""
    name = name.strip()
    return BROADCASTER_MAP.get(name, name)


def classify_broadcaster(name: str) -> str:
    """放送局を地上波/BS/ネット配信に分類する"""
    if name in TERRESTRIAL_BROADCASTERS:
        return "onair"
    elif name in BS_BROADCASTERS:
        return "bs"
    elif name in NET_BROADCASTERS:
        return "net"
    else:
        return "onair"  # デフォルトは地上波扱い


def scrape_with_requests(url: str):
    """
    requestsライブラリを使ってページを取得する。
    Goal.comはJavaScriptレンダリングが必要な場合があるため、
    失敗した場合はSeleniumにフォールバックする。
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError(
            "requests, beautifulsoup4 が未インストールです。\n"
            "pip install requests beautifulsoup4 を実行してください。"
        )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    res = requests.get(url, headers=headers, timeout=30)
    res.raise_for_status()
    res.encoding = "utf-8"
    return BeautifulSoup(res.text, "html.parser")


def scrape_with_selenium(url: str):
    """
    SeleniumでChromeを起動し、JavaScriptレンダリング後のページを取得する。
    ChromeDriverが必要: pip install selenium
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from bs4 import BeautifulSoup
        import time
    except ImportError:
        raise ImportError(
            "selenium, beautifulsoup4 が未インストールです。\n"
            "pip install selenium beautifulsoup4 を実行してください。\n"
            "また Chrome と ChromeDriver が必要です。"
        )

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=ja-JP")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    try:
        print("  Chromeでページを読み込み中... (最大15秒待機)")
        driver.get(url)

        # ページ内のコンテンツが描画されるまで待つ
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
        except Exception:
            # タイムアウトしてもページソースを取得する
            import time
            time.sleep(8)

        return BeautifulSoup(driver.page_source, "html.parser")
    finally:
        driver.quit()


def parse_date_text(text: str) -> str:
    """
    テキストから日付を抽出する。
    例: "6月15日" → "6/15", "2026/06/15" → "6/15"
    """
    # 「6月15日」形式
    m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}"

    # 「6/15」または「2026/6/15」形式
    m = re.search(r"(?:2026/)?(\d{1,2})/(\d{1,2})", text)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}"

    return ""


def parse_time_text(text: str) -> str:
    """
    テキストからキックオフ時刻（日本時間）を抽出する。
    例: "05:00 (JST)" → "05:00"
    """
    m = re.search(r"(\d{1,2}):(\d{2})", text)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return ""


def parse_broadcast(text: str):
    """
    Goal.comの放送テキストを解析して (broadcasters, tv_bsp4k, bsp4k_live) を返す。
    例: "TV：フジテレビ、NHK BS、NHK BSP4K(録)ネット：DAZN"
         "TV：NHK総合、NHK BSP4K(生)ネット：DAZN"
    """
    broadcasters = []
    tv_bsp4k = False
    bsp4k_live = False

    # TV部分とネット部分に分割（"ネット："または"ネット:" で区切る）
    net_sep = re.search(r"ネット[：:]", text)
    if net_sep:
        tv_part  = text[:net_sep.start()]
        net_part = text[net_sep.end():]
    else:
        tv_part, net_part = text, ""

    # BSP4K の有無と生/録を判定
    if "BSP4K" in tv_part:
        tv_bsp4k = True
        # BSP4K直後の括弧内が "生" なら LIVE
        m = re.search(r"BSP4K\s*[（(]([^)）]+)[)）]", tv_part)
        if m and "生" in m.group(1):
            bsp4k_live = True

    # BSP4K 部分をTV文字列から除去して他の放送局を抽出
    tv_clean = re.sub(r"TV[：:]", "", tv_part)
    tv_clean = re.sub(r"NHK\s*BSP4K[（(][^)）]*[)）]", "", tv_clean)
    tv_clean = re.sub(r"NHK\s*BSP4K", "", tv_clean)

    for part in tv_clean, net_part:
        for bc in re.split(r"[、,，]", part):
            bc = bc.strip()
            if not bc:
                continue
            bc = re.sub(r"[（(][^)）]*[)）]", "", bc).strip()  # カッコ補足を除去
            if not bc:
                continue
            normalized = normalize_broadcaster(bc)
            if normalized and normalized not in broadcasters:
                broadcasters.append(normalized)

    return broadcasters, tv_bsp4k, bsp4k_live


def parse_matches_from_soup(soup) -> list:
    """
    BeautifulSoupオブジェクトからGoal.comの試合データを解析する。

    Goal.comの実際のHTML構造:
      <h3>6月30日(火)</h3>  ← 日付見出し（テーブルの親コンテナ内）
      <table>
        <tr><th>No.</th><th>時間</th><th>ラウンド</th><th>カード</th><th>放送予定</th></tr>
        <tr><td>2</td><td>2:00</td><td>ラウンド32</td>
            <td>ブラジル vs 日本</td>
            <td>TV：フジテレビ、NHK BS、NHK BSP4K(録)ネット：DAZN</td></tr>
        ...
      </table>
    """
    matches = []
    date_pat = re.compile(r"(\d{1,2})月(\d{1,2})日")

    # --- 方法1: テーブル + 親コンテナ内の見出しから日付を取得 ---
    tables = soup.find_all("table")
    if tables:
        print(f"  テーブル形式のデータを検出 ({len(tables)}個のテーブル)")

        for table in tables:
            # テーブルの親コンテナをたどってh2/h3/strong等で日付を探す
            date_str = ""
            container = table.parent
            for _ in range(6):
                for tag in ["h2", "h3", "h4", "strong", "b", "p"]:
                    for el in container.find_all(tag):
                        dm = date_pat.search(el.get_text())
                        if dm:
                            date_str = f"{int(dm.group(1))}/{int(dm.group(2))}"
                            break
                    if date_str:
                        break
                if date_str:
                    break
                if container.parent:
                    container = container.parent

            if not date_str:
                continue  # 日付が見つからないテーブルはスキップ

            rows = table.find_all("tr")
            for row in rows[1:]:  # 1行目はヘッダー（No./時間/ラウンド/カード/放送予定）
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) < 5:
                    continue

                time_str = parse_time_text(cells[1])
                if not time_str:
                    continue

                stage    = cells[2]
                card     = cells[3]   # "チーム1 vs チーム2"
                broadcast = cells[4]  # "TV：... ネット：..."

                # チーム名を "vs" で分割
                vs_parts = re.split(r"\s*vs\.?\s*", card, maxsplit=1, flags=re.I)
                if len(vs_parts) != 2:
                    continue
                team1, team2 = vs_parts[0].strip(), vs_parts[1].strip()
                if not team1 or not team2:
                    continue

                broadcasters, tv_bsp4k, bsp4k_live = parse_broadcast(broadcast)
                match = _build_match(date_str, time_str, stage, team1, team2, broadcasters, None)
                match["tv_bsp4k"]   = tv_bsp4k
                match["bsp4k_live"] = bsp4k_live
                matches.append(match)

    if matches:
        return matches

    # --- フォールバック: テキストパターンマッチング ---
    articles = soup.find_all(["article", "section", "div"],
                              class_=re.compile(r"match|game|fixture|schedule|tv", re.I))
    print(f"  リスト形式のデータを検出 ({len(articles)}個の要素)")
    if articles:
        current_date = ""
        for element in articles:
            text = element.get_text(separator=" ", strip=True)
            date_candidate = parse_date_text(text)
            if date_candidate:
                current_date = date_candidate
            time_str = parse_time_text(text)
            if time_str and current_date:
                match = _try_parse_element(element, current_date, time_str)
                if match:
                    matches.append(match)

    if not matches:
        print("  テキストパターンマッチングで抽出を試みます...")
        matches = parse_matches_from_text(soup.get_text(separator="\n"))

    return matches


def _try_parse_row(cells: list, date: str) -> dict | None:
    """テーブルの1行から試合データを組み立てる"""
    # 時刻を探す
    time_str = ""
    team1 = ""
    team2 = ""
    broadcasters = []

    score = None
    for cell in cells:
        if not time_str:
            t = parse_time_text(cell)
            if t:
                time_str = t
                continue
        # スコア（数字-数字）を検出
        if score is None:
            score = parse_score_from_text(cell)
        # vs / − で区切られたチーム名を探す
        if not team1:
            vs_match = re.split(r"\s+vs\.?\s+|\s+−\s+|\s+対\s+", cell, maxsplit=1, flags=re.I)
            if len(vs_match) == 2:
                team1, team2 = vs_match[0].strip(), vs_match[1].strip()
                continue
        # 放送局っぽい文字列
        if any(b in cell for b in ["NHK", "テレビ", "フジ", "DAZN", "ABEMA", "BS"]):
            name = normalize_broadcaster(cell)
            if name:
                broadcasters.append(name)

    if not (time_str and (team1 or len(cells) >= 4)):
        return None

    return _build_match(date, time_str, "", team1, team2, broadcasters, score)


def _try_parse_element(element, date: str, time_str: str) -> dict | None:
    """HTML要素から試合データを組み立てる"""
    text = element.get_text(separator=" ", strip=True)

    # チーム名（vs で区切られた部分）
    team1, team2 = "", ""
    vs_match = re.search(r"(.+?)\s+vs\.?\s+(.+?)(?:\s|$)", text, re.I)
    if vs_match:
        team1 = vs_match.group(1).strip()
        team2 = vs_match.group(2).strip()

    # スコア
    score = parse_score_from_text(text)

    # 放送局
    broadcasters = []
    for key in BROADCASTER_MAP:
        if key in text:
            normalized = normalize_broadcaster(key)
            if normalized not in broadcasters:
                broadcasters.append(normalized)

    if not team1:
        return None

    return _build_match(date, time_str, "", team1, team2, broadcasters, score)


def parse_score_from_text(text: str) -> dict | None:
    """
    テキストからスコアを解析する。
    例: "2-1", "3 - 0", "(2-1)" → {"home": 2, "away": 1}
    """
    m = re.search(r"\b(\d{1,2})\s*[-−]\s*(\d{1,2})\b", text)
    if m:
        home = int(m.group(1))
        away = int(m.group(2))
        # 異常値を除外（スコアとして意味のある範囲）
        if home <= 20 and away <= 20:
            return {"home": home, "away": away}
    return None


def is_real_team(name: str) -> bool:
    """チーム名が確定済みか（"Match X 勝者" や "No.X" でないか）を判定する"""
    return not any(x in name for x in ["勝者", "敗者", "No.", "Match "])


def parse_card(card: str) -> dict | None:
    """
    カード文字列からチーム名とスコアを解析する。
    通常: "ブラジル 2-1 日本"              → {team1, score1, score2, team2}
    PK戦: "ドイツ 1 ( 3PK4 ) 1 パラグアイ" → {team1, score1, score2, team2, pk1, pk2}
    未来の試合 "カナダ vs モロッコ"         → {team1, team2}  ← スコアなし
    未確定 "Match 80 勝者 vs ..."          → None
    """
    pk_pat = re.compile(r"\(\s*(\d+)\s*PK\s*(\d+)\s*\)", re.I)
    pk_m = pk_pat.search(card)

    if pk_m:
        before = card[:pk_m.start()].strip()
        after  = card[pk_m.end():].strip()
        m1 = re.match(r"^(.+?)\s+(\d+)$", before)
        m2 = re.match(r"^(\d+)\s+(.+?)$", after)
        if m1 and m2:
            return {
                "team1": m1.group(1).strip(), "score1": int(m1.group(2)),
                "score2": int(m2.group(1)),   "team2": m2.group(2).strip(),
                "pk1": int(pk_m.group(1)),    "pk2": int(pk_m.group(2))
            }

    # 通常スコア: "チーム1 X-Y チーム2"
    m = re.match(r"^(.+?)\s+(\d+)\s*[-－]\s*(\d+)\s+(.+?)$", card.strip())
    if m:
        return {
            "team1": m.group(1).strip(), "score1": int(m.group(2)),
            "score2": int(m.group(3)),   "team2": m.group(4).strip()
        }

    # チーム名のみ（未来の試合）: "チーム1 vs チーム2"
    m = re.match(r"^(.+?)\s+vs\s+(.+?)$", card.strip(), re.I)
    if m:
        t1 = m.group(1).strip()
        t2 = m.group(2).strip()
        # 両方とも確定済みチーム名の場合のみ返す
        if is_real_team(t1) and is_real_team(t2):
            return {"team1": t1, "team2": t2}

    return None


def scrape_scores() -> dict:
    """
    Goal.com の試合結果ページからスコアを取得する。
    戻り値: {(date, time): card_dict} の辞書
      card_dict: {team1, score1, score2, team2[, pk1, pk2]}

    Goal.com の試合結果ページ構造:
      テーブル列: [日時, Match Number, カード, 会場]
      通常カード: "ブラジル 2-1 日本"
      PK戦カード: "ドイツ 1 ( 3PK4 ) 1 パラグアイ"
    """
    print(f"\n【スコア取得】{RESULTS_URL}")
    try:
        soup = scrape_with_requests(RESULTS_URL)
    except Exception as e:
        print(f"  ❌ スコアページの取得に失敗: {e}")
        return {}

    scores = {}
    teams  = {}
    datetime_pat = re.compile(r"2026/(\d{1,2})/(\d{1,2})[^0-9]*(\d{1,2}):(\d{2})")

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_text = rows[0].get_text()
        if "日時" not in header_text and "カード" not in header_text:
            continue

        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 3:
                continue

            dt_text = cells[0]
            card    = cells[2]

            dm = datetime_pat.search(dt_text)
            if not dm:
                continue
            date     = f"{int(dm.group(1))}/{int(dm.group(2))}"
            time_str = f"{int(dm.group(3)):02d}:{dm.group(4)}"

            parsed = parse_card(card)
            if not parsed:
                continue

            if "score1" in parsed:
                scores[(date, time_str)] = parsed
            else:
                # チーム名のみ（スコアなし）
                teams[(date, time_str)] = parsed

    print(f"  ✅ スコア取得: {len(scores)} 試合 / チーム名確定: {len(teams)} 試合")
    return scores, teams


def update_inline_matches_scores(scores: dict):
    """
    index.html の INLINE_MATCHES エントリの score フィールドをスコアで更新する。
    チーム名を比較してスコアの home/away を INLINE_MATCHES のチーム順に合わせる。
    """
    if not os.path.exists(INDEX_HTML):
        print(f"  ⚠️  index.html が見つかりません: {INDEX_HTML}")
        return

    with open(INDEX_HTML, encoding="utf-8") as f:
        lines = f.readlines()

    entry_pat = re.compile(
        r'^\s+\{"date":"([^"]+)","time":"([^"]+)",.+"team1":"([^"]+)","team2":"([^"]+)",.+"score":(null|\{[^}]+\})'
    )

    updated = 0
    new_lines = []

    for line in lines:
        m = entry_pat.match(line)
        if not m:
            new_lines.append(line)
            continue

        date     = m.group(1)
        time_str = m.group(2)
        team1    = m.group(3)
        old_score = m.group(5)

        key = (date, time_str)
        if key not in scores:
            new_lines.append(line)
            continue

        s = scores[key]
        # チーム名を比較してスコアの向きを決定
        if team1 == s["team1"]:
            t1_score, t2_score = s["score1"], s["score2"]
            pk1 = s.get("pk1")
            pk2 = s.get("pk2")
        else:
            t1_score, t2_score = s["score2"], s["score1"]
            pk1 = s.get("pk2")
            pk2 = s.get("pk1")

        score_obj = {"home": t1_score, "away": t2_score}
        if pk1 is not None:
            score_obj["pk_home"] = pk1
            score_obj["pk_away"] = pk2

        score_json = json.dumps(score_obj, ensure_ascii=False)
        new_line = line.replace(f'"score":{old_score}', f'"score":{score_json}', 1)

        if new_line != line:
            updated += 1
        new_lines.append(new_line)

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"  ✅ INLINE_MATCHES のスコアを {updated} 件更新しました")


def update_inline_matches_teams(teams: dict):
    """
    index.html の INLINE_MATCHES で team1/team2 が「未定」のエントリを
    確定済みチーム名で更新する。
    """
    if not os.path.exists(INDEX_HTML):
        return

    with open(INDEX_HTML, encoding="utf-8") as f:
        lines = f.readlines()

    entry_pat = re.compile(
        r'^\s+\{"date":"([^"]+)","time":"([^"]+)",.+"team1":"([^"]+)","team2":"([^"]+)"'
    )

    updated = 0
    new_lines = []

    for line in lines:
        m = entry_pat.match(line)
        if not m:
            new_lines.append(line)
            continue

        date     = m.group(1)
        time_str = m.group(2)
        team1    = m.group(3)
        team2    = m.group(4)

        key = (date, time_str)
        if key not in teams:
            new_lines.append(line)
            continue

        t = teams[key]
        new_t1 = t["team1"]
        new_t2 = t["team2"]

        # 未定のチームのみ更新（is_real_team でフィルタ済みだが念のため）
        if not is_real_team(new_t1) or not is_real_team(new_t2):
            new_lines.append(line)
            continue

        new_line = line
        if team1 == "未定" and is_real_team(new_t1):
            new_line = new_line.replace(f'"team1":"未定"', f'"team1":"{new_t1}"', 1)
        if team2 == "未定" and is_real_team(new_t2):
            new_line = new_line.replace(f'"team2":"未定"', f'"team2":"{new_t2}"', 1)

        if new_line != line:
            updated += 1
        new_lines.append(new_line)

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"  ✅ INLINE_MATCHES のチーム名を {updated} 件更新しました")


def _build_match(date: str, time_str: str, stage: str,
                 team1: str, team2: str, broadcasters: list,
                 score: dict | None = None) -> dict:
    """試合データの辞書を組み立てる"""
    tv_onair = [b for b in broadcasters if classify_broadcaster(b) == "onair"]
    tv_bs    = [b for b in broadcasters if classify_broadcaster(b) == "bs"]
    tv_net   = [b for b in broadcasters if classify_broadcaster(b) == "net"]

    is_japan = any(name in team1 or name in team2 for name in JAPAN_NAMES)
    # 地上波またはNHK BSで生中継される試合かどうか
    is_live_broadcast = len(tv_onair) > 0 or len(tv_bs) > 0

    return {
        "date": date,
        "time": time_str,
        "stage": stage,
        "team1": team1,
        "team2": team2,
        "tv_onair": tv_onair,
        "tv_bs": tv_bs,
        "tv_net": tv_net,
        "tv_bsp4k": True,            # BSP4Kは全試合録画放送
        "bsp4k_live": False,          # BSP4K生中継かどうか（デフォルト: 録画）
        "is_live_broadcast": is_live_broadcast,
        "score": score,
        "is_japan": is_japan,
    }


def parse_matches_from_text(text: str) -> list:
    """
    ページのテキスト全体から試合データをパターンマッチングで抽出する。
    Goal.comの実際のページ構造が不明な場合のフォールバック処理。
    """
    matches = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    current_date = ""
    # 日付パターン: 「6月15日」「6/15」など
    date_pattern = re.compile(r"(\d{1,2})[月/](\d{1,2})日?")
    # 時刻パターン: 「05:00」「午前5時」など
    time_pattern = re.compile(r"(\d{1,2}):(\d{2})")
    # チーム名とvs
    vs_pattern = re.compile(r"(.{2,20})\s+(?:vs\.?|対)\s+(.{2,20})", re.I)

    i = 0
    while i < len(lines):
        line = lines[i]

        # 日付を検出
        dm = date_pattern.search(line)
        if dm and not time_pattern.search(line):
            current_date = f"{int(dm.group(1))}/{int(dm.group(2))}"
            i += 1
            continue

        # 試合行を検出（時刻 + チーム情報を含む行）
        tm = time_pattern.search(line)
        vs_m = vs_pattern.search(line)

        if tm and current_date:
            time_str = f"{int(tm.group(1)):02d}:{tm.group(2)}"
            team1, team2 = "", ""

            if vs_m:
                team1 = vs_m.group(1).strip()
                team2 = vs_m.group(2).strip()

            # 放送局を現在行と前後行から検索
            context = " ".join(lines[max(0, i-1):min(len(lines), i+3)])
            broadcasters = []
            for key in BROADCASTER_MAP:
                if key in context:
                    normalized = normalize_broadcaster(key)
                    if normalized not in broadcasters:
                        broadcasters.append(normalized)

            # スコア
            score = parse_score_from_text(context)

            if team1 and team2:
                match = _build_match(current_date, time_str, "", team1, team2, broadcasters, score)
                matches.append(match)

        i += 1

    return matches


def print_summary(matches: list):
    """取得結果のサマリーを表示する"""
    print("\n" + "=" * 50)
    print(f"✅ {len(matches)}試合のデータを取得しました")
    japan_matches = [m for m in matches if m.get("is_japan")]
    onair_matches = [m for m in matches if m.get("tv_onair")]
    print(f"  日本戦: {len(japan_matches)}試合")
    print(f"  地上波放送あり: {len(onair_matches)}試合")

    if matches:
        dates = sorted(set(m["date"] for m in matches),
                       key=lambda d: [int(x) for x in d.split("/")])
        print(f"  期間: {dates[0]} 〜 {dates[-1]}")
    print("=" * 50)


def main():
    print("=" * 50)
    print("W杯2026 TV放送スケジュール スクレイパー")
    print("=" * 50)
    print(f"\nスクレイピング対象:\n  {URL}\n")

    soup = None

    # ステップ1: requestsで試みる
    print("【ステップ1】requestsでページ取得を試みます...")
    try:
        soup = scrape_with_requests(URL)
        title = soup.find("title")
        print(f"  ✅ 取得成功 (タイトル: {title.get_text() if title else '不明'})")
    except Exception as e:
        print(f"  ❌ 失敗: {e}")

    # ステップ2: requestsで取得できたが内容が不十分な場合もSeleniumを試みる
    # （JavaScriptレンダリングが必要なサイトでは空のbodyになることがある）
    if soup is None or len(soup.get_text()) < 1000:
        print("\n【ステップ2】Seleniumでの再試行...")
        print("  (Chrome と ChromeDriver が必要です)")
        try:
            soup = scrape_with_selenium(URL)
            title = soup.find("title")
            print(f"  ✅ 取得成功 (タイトル: {title.get_text() if title else '不明'})")
        except ImportError as e:
            print(f"  ⚠️  Selenium未インストール: {e}")
        except Exception as e:
            print(f"  ❌ Selenium失敗: {e}")

    if soup is None:
        print("\n❌ エラー: ページを取得できませんでした。")
        print("  インターネット接続と以下の点を確認してください:")
        print("  - pip install requests beautifulsoup4")
        print("  - pip install selenium  (Seleniumの場合)")
        print("  - ChromeDriver のインストール (Seleniumの場合)")
        sys.exit(1)

    # ステップ3: データ解析
    print("\n【ステップ3】試合データを解析中...")
    matches = parse_matches_from_soup(soup)

    if not matches:
        print("\n⚠️  警告: 試合データを取得できませんでした。")
        print("  考えられる原因:")
        print("  1. Goal.comのHTMLが想定と異なる構造になっている")
        print("  2. JavaScript レンダリングが必要 (Seleniumを試してください)")
        print("  3. ページが地域制限されている")
        print("\n  scraper.py 内の parse_matches_from_soup() 関数を")
        print("  実際のHTML構造に合わせて調整してください。")
        print("\n  ヒント: ページのHTMLを確認するには以下を実行してください:")
        print("    python -c \"")
        print("    import requests")
        print("    r = requests.get('URL', headers={'User-Agent': 'Mozilla/5.0'})")
        print("    print(r.text[:3000])\"")
        print("\n  matches.json は更新されませんでした。")
        sys.exit(1)

    # ステップ4: スコア＆チーム名を取得してマージ
    print("\n【ステップ4】試合結果（スコア・チーム名）を取得中...")
    scores, teams = scrape_scores()

    # matches.json へのスコアマージ
    merged = 0
    for m in matches:
        key = (m["date"], m["time"])
        if key in scores:
            s = scores[key]
            if m["team1"] == s["team1"]:
                t1, t2, pk1, pk2 = s["score1"], s["score2"], s.get("pk1"), s.get("pk2")
            else:
                t1, t2, pk1, pk2 = s["score2"], s["score1"], s.get("pk2"), s.get("pk1")
            score_obj = {"home": t1, "away": t2}
            if pk1 is not None:
                score_obj["pk_home"] = pk1
                score_obj["pk_away"] = pk2
            m["score"] = score_obj
            merged += 1
    print(f"  matches.json へのスコアマージ: {merged} 件")

    # index.html の INLINE_MATCHES を更新（スコア＋チーム名）
    print("\n【ステップ4b】index.html の INLINE_MATCHES を更新中...")
    update_inline_matches_scores(scores)
    update_inline_matches_teams(teams)

    # ステップ5: 保存
    print(f"\n【ステップ5】{OUTPUT_FILE} に保存中...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    print_summary(matches)
    print(f"\n✅ matches.json を保存しました: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
