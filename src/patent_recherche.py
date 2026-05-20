"""
Patent-Recherche Automatisierung – 100% KOSTENLOS
Thema: KI-Sicherheitsfunktionen in Maschinen / AI Safety Patents

Keine API-Keys erforderlich!

Installation:
 pip install requests pandas openpyxl matplotlib seaborn beautifulsoup4 lxml
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────

OUTPUT_DIR = Path("patent_recherche_output")
OUTPUT_DIR.mkdir(exist_ok=True)

DATA_DIR = Path(__file__).parent.parent / "data"

DATE_FROM = "2019-01-01"
DATE_TO   = datetime.today().strftime("%Y-%m-%d")

SEARCH_QUERIES = [
    "artificial intelligence safety function machinery",
    "machine learning functional safety industrial",
    "neural network safety-critical machine",
    "AI hazard detection robot safety",
    "deep learning safety monitoring industrial",
    "autonomous system safety assurance",
    "AI risk assessment industrial equipment",
    "machine learning safety certification",
    "AI safety constraint enforcement robot",
    "explainable AI safety industrial control",
]

IPC_COMBINATIONS = [
    ("G06N", "F16P"),
    ("G06N", "B25J"),
    ("G06N", "G05B"),
    ("G06N", "B60W"),
    ("G06N", "G05D"),
    ("G06N", "F16H"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

MAX_RESULTS_PER_QUERY = 40


def _normalize_people_or_org(value) -> str:
    """Normalisiert API-Felder wie assignee/inventor zu einem sauberen String."""
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    if isinstance(value, str):
        text = value.strip()
        if ", " in text:
            parts = [p.strip() for p in text.split(",")]
            if len(parts) >= 4 and all(len(p) == 1 for p in parts if p):
                return "".join(parts)
        return text
    return ""


# ─────────────────────────────────────────────
# 1. GOOGLE PATENTS (kostenlos via XHR)
# ─────────────────────────────────────────────

def search_google_patents(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> list[dict]:
    """Sucht Patente direkt auf Google Patents (kein API-Key nötig)."""
    print(f"  [Google Patents] Suche: '{query}'")
    url = "https://patents.google.com/xhr/query"
    params = {
        "url":     f"q={requests.utils.quote(query)}&after=priority:{DATE_FROM.replace('-','')}&num={max_results}",
        "exp":     "",
        "timeout": 10000,
    }
    patents = []
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", {}).get("cluster", [])
        for cluster in results:
            for r in cluster.get("result", []):
                pat = r.get("patent", {})
                patents.append({
                    "source":      "Google Patents",
                    "title":       pat.get("title", ""),
                    "patent_id":   pat.get("publication_number", ""),
                    "assignee":    _normalize_people_or_org(pat.get("assignee", [])),
                    "inventor":    _normalize_people_or_org(pat.get("inventor", [])),
                    "filing_date": pat.get("filing_date", ""),
                    "grant_date":  pat.get("grant_date", ""),
                    "abstract":    pat.get("abstract", ""),
                    "url":         f"https://patents.google.com/patent/{pat.get('publication_number','')}",
                    "query":       query,
                })
    except Exception as e:
        print(f"    Fehler Google Patents: {e}")
    return patents


# ─────────────────────────────────────────────
# 2. ABSTRACT + IPC ENRICHMENT (Google Patents HTML)
# ─────────────────────────────────────────────

def fetch_patent_details(patent_id: str, url: str) -> dict:
    """Fetch abstract and IPC/CPC codes from an individual Google Patents page."""
    result = {"abstract": "", "ipc_codes": ""}
    if not url or "google.com/patent" not in url:
        return result
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Abstract — try several selectors in order of preference
        abstract = ""
        abs_section = soup.find("section", {"itemprop": "abstract"})
        if abs_section:
            inner = abs_section.find("div", class_="abstract") or abs_section
            abstract = inner.get_text(separator=" ", strip=True)
        if not abstract:
            div = soup.find("div", class_="abstract")
            if div:
                abstract = div.get_text(separator=" ", strip=True)
        if not abstract:
            meta = soup.find("meta", {"name": "description"})
            if meta:
                abstract = meta.get("content", "")
        result["abstract"] = abstract.strip()

        # IPC / CPC codes
        codes = []
        for span in soup.select("span[itemprop='Code']"):
            code = span.get_text(strip=True)
            if code and re.match(r"^[A-Z]\d{2}[A-Z]", code):
                codes.append(code)
        seen: set[str] = set()
        unique_codes: list[str] = []
        for c in codes:
            if c not in seen:
                seen.add(c)
                unique_codes.append(c)
            if len(unique_codes) >= 12:
                break
        result["ipc_codes"] = ", ".join(unique_codes)

    except Exception as e:
        print(f" [err: {e}]", end="")
    return result


def enrich_with_details(df: pd.DataFrame) -> pd.DataFrame:
    """
    Second-pass enrichment: fetch abstract + IPC codes from Google Patents
    individual pages using browser-like headers.
    """
    if "ipc_codes" not in df.columns:
        df = df.copy()
        df["ipc_codes"] = ""

    needs = df["abstract"].fillna("").str.strip() == ""
    to_enrich = df[needs].copy()
    already   = df[~needs].copy()

    total = len(to_enrich)
    print(f"\n[Enrichment] {total} Patente ohne Abstract (ca. {total * 3 // 60 + 1} min)...")

    new_abstracts = []
    new_ipc       = []

    for i, (_, row) in enumerate(to_enrich.iterrows(), 1):
        pid = row["patent_id"]
        url = row.get("url", "")
        print(f"  [{i:>3}/{total}] {pid}", end="", flush=True)
        details = fetch_patent_details(pid, url)
        new_abstracts.append(details["abstract"])
        new_ipc.append(details["ipc_codes"])
        marker = " ✓" if details["abstract"] else " —"
        print(marker)
        time.sleep(2.5)

    to_enrich = to_enrich.copy()
    to_enrich["abstract"]  = new_abstracts
    to_enrich["ipc_codes"] = new_ipc

    if "ipc_codes" not in already.columns:
        already = already.copy()
        already["ipc_codes"] = ""

    result = pd.concat([already, to_enrich], ignore_index=True)
    filled = (result["abstract"].fillna("").str.strip() != "").sum()
    print(f"  Abstracts vorhanden: {filled}/{len(result)}")
    return result


# ─────────────────────────────────────────────
# 3. EPO ESPACENET
# ─────────────────────────────────────────────

def search_epo(ipc_a: str, ipc_b: str, max_results: int = 25) -> list[dict]:
    """Sucht Patente auf Espacenet über IPC-Klassenkombination (kostenlos)."""
    print(f"  [EPO OPS] IPC-Suche: {ipc_a} + {ipc_b}")
    url = "https://worldwide.espacenet.com/patent/search"
    params = {"q": f"cl={ipc_a} AND cl={ipc_b}"}
    patents = []
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("article.patent-result") or soup.select("[data-publication-number]")
        for item in items[:max_results]:
            pid      = item.get("data-publication-number", "")
            title    = item.select_one("h3, .title")
            assignee = item.select_one(".applicant, .assignee")
            patents.append({
                "source":      "Espacenet (EPO)",
                "title":       title.get_text(strip=True) if title else "",
                "patent_id":   pid,
                "assignee":    assignee.get_text(strip=True) if assignee else "",
                "inventor":    "",
                "filing_date": "",
                "grant_date":  "",
                "abstract":    "",
                "ipc_codes":   "",
                "url":         f"https://worldwide.espacenet.com/patent/search?q=pn%3D{pid}",
                "query":       f"{ipc_a}+{ipc_b}",
            })
        if not patents:
            ids = re.findall(r"\b([A-Z]{2}\d{6,}[A-Z]\d?)\b", resp.text)
            for pid in list(set(ids))[:max_results]:
                patents.append({
                    "source":      "Espacenet (EPO)",
                    "title":       "",
                    "patent_id":   pid,
                    "assignee":    "",
                    "inventor":    "",
                    "filing_date": "",
                    "grant_date":  "",
                    "abstract":    "",
                    "ipc_codes":   "",
                    "url":         f"https://worldwide.espacenet.com/patent/search?q=pn%3D{pid}",
                    "query":       f"{ipc_a}+{ipc_b}",
                })
    except Exception as e:
        print(f"    Fehler EPO: {e}")
    return patents


# ─────────────────────────────────────────────
# 4. DPMA DEPATISnet
# ─────────────────────────────────────────────

def search_dpma(query: str, max_results: int = 20) -> list[dict]:
    """Sucht deutsche Patente über DEPATISnet (kostenlos)."""
    print(f"  [DPMA] Suche: '{query}'")
    url = "https://depatisnet.dpma.de/DepatisNet/depatisnet"
    params = {
        "action":   "bibdat",
        "so":       "pd desc",
        "hits":     max_results,
        "firstdoc": 1,
        "query":    f"ti=({query}) AND isd>={DATE_FROM.replace('-', '')}",
    }
    patents = []
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.select("tr.result-row, tr[id^='doc']")
        for row in rows[:max_results]:
            cells = row.find_all("td")
            if len(cells) >= 3:
                pid      = cells[0].get_text(strip=True)
                title    = cells[1].get_text(strip=True)
                assignee = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                date     = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                if pid:
                    patents.append({
                        "source":      "DPMA DEPATISnet",
                        "title":       title,
                        "patent_id":   pid,
                        "assignee":    assignee,
                        "inventor":    "",
                        "filing_date": date,
                        "grant_date":  "",
                        "abstract":    "",
                        "ipc_codes":   "",
                        "url":         f"https://depatisnet.dpma.de/DepatisNet/depatisnet?action=bibdat&docid={pid}",
                        "query":       query,
                    })
        if not patents:
            ids = re.findall(r"docid=([A-Z]{2}\d+[A-Z]\d?)", resp.text)
            for pid in list(set(ids))[:max_results]:
                patents.append({
                    "source":      "DPMA DEPATISnet",
                    "title":       "",
                    "patent_id":   pid,
                    "assignee":    "",
                    "inventor":    "",
                    "filing_date": "",
                    "grant_date":  "",
                    "abstract":    "",
                    "ipc_codes":   "",
                    "url":         f"https://depatisnet.dpma.de/DepatisNet/depatisnet?action=bibdat&docid={pid}",
                    "query":       query,
                })
    except Exception as e:
        print(f"    Fehler DPMA: {e}")
    return patents


# ─────────────────────────────────────────────
# 5. WIPO PatentScope
# ─────────────────────────────────────────────

def search_wipo(query: str, max_results: int = 20) -> list[dict]:
    """Sucht PCT-Anmeldungen über WIPO PatentScope (kostenlos)."""
    print(f"  [WIPO] Suche: '{query}'")
    url = "https://patentscope.wipo.int/search/en/results.jsf"
    params = {
        "query":    f"ALLTXT:({query})",
        "pageSize": max_results,
    }
    patents = []
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.select(".ps-patent-result, tr.resultRow")
        for row in rows[:max_results]:
            pid_el   = row.select_one(".patnum, .pub-number")
            title_el = row.select_one(".trans-title, .title")
            app_el   = row.select_one(".applicant")
            date_el  = row.select_one(".pub-date, .filing-date")
            pid = pid_el.get_text(strip=True) if pid_el else ""
            if pid:
                patents.append({
                    "source":      "WIPO PatentScope",
                    "title":       title_el.get_text(strip=True) if title_el else "",
                    "patent_id":   pid,
                    "assignee":    app_el.get_text(strip=True) if app_el else "",
                    "inventor":    "",
                    "filing_date": date_el.get_text(strip=True) if date_el else "",
                    "grant_date":  "",
                    "abstract":    "",
                    "ipc_codes":   "",
                    "url":         f"https://patentscope.wipo.int/search/en/detail.jsf?docId={pid.replace('/', '')}",
                    "query":       query,
                })
        if not patents:
            ids = re.findall(r"WO\s?\d{4}[/\-]\d{6}", resp.text)
            for pid in list(set(ids))[:max_results]:
                pid_clean = pid.replace(" ", "")
                patents.append({
                    "source":      "WIPO PatentScope",
                    "title":       "",
                    "patent_id":   pid_clean,
                    "assignee":    "",
                    "inventor":    "",
                    "filing_date": "",
                    "grant_date":  "",
                    "abstract":    "",
                    "ipc_codes":   "",
                    "url":         f"https://patentscope.wipo.int/search/en/detail.jsf?docId={pid_clean.replace('/', '')}",
                    "query":       query,
                })
    except Exception as e:
        print(f"    Fehler WIPO: {e}")
    return patents


# ─────────────────────────────────────────────
# 6. DATENBEREINIGUNG & DEDUPLIZIERUNG
# ─────────────────────────────────────────────

def clean_and_deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Bereinigt und dedupliziert den Datensatz."""
    print("\n[Bereinigung] Starte Deduplizierung...")
    before = len(df)
    for col in ["patent_id", "title", "assignee", "inventor", "abstract", "query", "source", "ipc_codes"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    df["patent_id"] = df["patent_id"].str.upper().str.strip()
    df["title"]     = df["title"].str.strip()
    df["assignee"]  = df["assignee"].apply(_normalize_people_or_org)
    df["inventor"]  = df["inventor"].apply(_normalize_people_or_org)
    for col in ["filing_date", "grant_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    # Keep row with longest abstract when deduplicating
    df = df.sort_values("abstract", key=lambda x: x.str.len(), ascending=False)
    df = df.drop_duplicates(subset=["patent_id"], keep="first")
    df = df[df["patent_id"].str.len() > 3]
    print(f"  Vorher: {before} | Nachher: {len(df)} | Entfernt: {before - len(df)}")
    return df.reset_index(drop=True)


# ─────────────────────────────────────────────
# 7. ZUSAMMENFASSUNG
# ─────────────────────────────────────────────

def summarize_results(df: pd.DataFrame) -> str:
    total         = len(df)
    sources       = df["source"].value_counts().to_dict()
    top_assignees = df[df["assignee"] != ""]["assignee"].value_counts().head(5).to_dict()
    with_abstract = (df["abstract"].fillna("").str.strip() != "").sum()
    year_range    = ""
    dates = pd.to_datetime(df["filing_date"], errors="coerce").dropna()
    if len(dates) > 0:
        year_range = f"{dates.min().year}–{dates.max().year}"

    lines = [
        "=" * 60,
        "  ZUSAMMENFASSUNG DER PATENTRECHERCHE",
        "=" * 60,
        f"  Gesamt gefundene Patente : {total}",
        f"  Mit Abstract             : {with_abstract} ({with_abstract*100//total if total else 0}%)",
        f"  Zeitraum                 : {year_range or 'k. A.'}",
        "",
        "  Patente nach Datenbank:",
    ]
    for src, cnt in sources.items():
        lines.append(f"    • {src}: {cnt}")
    lines += ["", "  Top-Anmelder:"]
    if top_assignees:
        for name, cnt in top_assignees.items():
            lines.append(f"    • {name}: {cnt} Patent(e)")
    else:
        lines.append("    (keine Anmelderdaten verfügbar)")
    lines += ["=" * 60]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 8. VISUALISIERUNG
# ─────────────────────────────────────────────

def visualize_results(df: pd.DataFrame):
    print("\n[Visualisierung] Erstelle Grafiken...")
    sns.set_theme(style="whitegrid", palette="muted")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Patentrecherche: KI-Sicherheitsfunktionen in Maschinen",
                 fontsize=14, fontweight="bold")

    ax1 = axes[0, 0]
    if df["filing_date"].notna().sum() > 0:
        df["year"] = df["filing_date"].dt.year
        df["year"].value_counts().sort_index().plot(kind="bar", ax=ax1,
                                                     color="steelblue", edgecolor="white")
        ax1.set_title("Patentanmeldungen pro Jahr")
        ax1.set_xlabel("Jahr")
        ax1.set_ylabel("Anzahl")
        ax1.tick_params(axis="x", rotation=45)
    else:
        ax1.text(0.5, 0.5, "Keine Datumsdaten verfügbar",
                 ha="center", va="center", transform=ax1.transAxes)
        ax1.set_title("Patentanmeldungen pro Jahr")

    ax2 = axes[0, 1]
    df["source"].value_counts().plot(kind="pie", ax=ax2, autopct="%1.1f%%", startangle=90)
    ax2.set_title("Patente nach Datenbank")
    ax2.set_ylabel("")

    ax3 = axes[1, 0]
    top = df[df["assignee"] != ""]["assignee"].value_counts().head(10)
    if not top.empty:
        top.sort_values().plot(kind="barh", ax=ax3, color="darkorange")
        ax3.set_title("Top 10 Anmelder")
        ax3.set_xlabel("Anzahl Patente")
    else:
        ax3.text(0.5, 0.5, "Keine Anmelderdaten verfügbar",
                 ha="center", va="center", transform=ax3.transAxes)
        ax3.set_title("Top 10 Anmelder")

    ax4 = axes[1, 1]
    qc = df["query"].value_counts().head(8)
    labels = [q[:35] + "…" if len(q) > 35 else q for q in qc.index]
    ax4.barh(labels, qc.values, color="seagreen")
    ax4.set_title("Treffer nach Suchanfrage")
    ax4.set_xlabel("Anzahl Patente")

    plt.tight_layout()
    out = OUTPUT_DIR / "patent_visualisierung.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  Grafik gespeichert: {out}")
    plt.show()


# ─────────────────────────────────────────────
# 9. EXPORT (CSV + Excel)
# ─────────────────────────────────────────────

def export_results(df: pd.DataFrame, summary: str, ts: str | None = None):
    """Speichert Ergebnisse als CSV (+ optional Excel) ins output- und data/-Verzeichnis."""
    if ts is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M")

    csv_path = OUTPUT_DIR / f"patente_{ts}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  CSV gespeichert:   {csv_path}")

    try:
        import openpyxl  # noqa: F401
        xlsx_path = OUTPUT_DIR / f"patente_{ts}.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Patente", index=False)
            pd.DataFrame({"Zusammenfassung": [summary]}).to_excel(
                writer, sheet_name="Zusammenfassung", index=False)
            pd.DataFrame({
                "Datenbank":      df["source"].value_counts().index,
                "Anzahl Patente": df["source"].value_counts().values,
            }).to_excel(writer, sheet_name="Statistiken", index=False)
        print(f"  Excel gespeichert: {xlsx_path}")
    except ImportError:
        print("  (openpyxl nicht installiert – Excel-Export übersprungen)")

    DATA_DIR.mkdir(exist_ok=True)
    data_csv = DATA_DIR / f"patente_{ts}.csv"
    df.to_csv(data_csv, index=False, encoding="utf-8-sig")
    print(f"  Dashboard-CSV:     {data_csv}")


# ─────────────────────────────────────────────
# HAUPTPROGRAMM
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Patent-Recherche (v2 – mit Abstract-Enrichment)")
    print(f"  Zeitraum: {DATE_FROM} bis {DATE_TO}")
    print("=" * 60)

    all_patents = []

    print("\n[1/4] Google Patents")
    for q in SEARCH_QUERIES:
        all_patents.extend(search_google_patents(q))
        time.sleep(2)

    print("\n[2/4] Espacenet (EPO)")
    for ipc_a, ipc_b in IPC_COMBINATIONS:
        all_patents.extend(search_epo(ipc_a, ipc_b))
        time.sleep(2)

    print("\n[3/4] DPMA DEPATISnet")
    for q in SEARCH_QUERIES[:4]:
        all_patents.extend(search_dpma(q))
        time.sleep(2)

    print("\n[4/4] WIPO PatentScope")
    for q in SEARCH_QUERIES[:4]:
        all_patents.extend(search_wipo(q))
        time.sleep(2)

    print(f"\n[Info] Gesamt gefunden (vor Bereinigung): {len(all_patents)}")
    df = pd.DataFrame(all_patents)

    if df.empty:
        print("Keine Ergebnisse gefunden. Bitte Internetverbindung prüfen.")
        return

    df = clean_and_deduplicate(df)
    print(f"[Info] Eindeutige Patente nach Bereinigung: {len(df)}")

    # Enrichment pass: fetch abstract + IPC codes for Google Patents results
    google_mask = df["source"] == "Google Patents"
    print(f"\n[Info] Google-Patents-Einträge für Enrichment: {google_mask.sum()}")
    df = enrich_with_details(df)

    summary = summarize_results(df)
    print("\n" + summary)

    export_results(df, summary)
    visualize_results(df)

    print(f"\n✓ Recherche abgeschlossen. Ergebnisse in: {OUTPUT_DIR.resolve()}")


def enrich_only(csv_path: str):
    """Load an existing CSV, run enrichment, and save an updated copy to data/."""
    print(f"[Enrich-only] Lade: {csv_path}")
    df = pd.read_csv(csv_path, dtype={"abstract": str, "ipc_codes": str})
    df["abstract"]  = df["abstract"].fillna("")
    df["ipc_codes"] = df["ipc_codes"].fillna("") if "ipc_codes" in df.columns else ""
    print(f"  {len(df)} Patente geladen, "
          f"{(df['abstract'].str.strip() == '').sum()} ohne Abstract.")
    df = enrich_with_details(df)
    summary = summarize_results(df)
    print("\n" + summary)
    ts = datetime.now().strftime("%Y%m%d_%H%M") + "_enriched"
    export_results(df, summary, ts=ts)
    print(f"\n✓ Enrichment abgeschlossen.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--enrich-only":
        enrich_only(sys.argv[2])
    else:
        main()
