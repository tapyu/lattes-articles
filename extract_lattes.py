#!/usr/bin/env python3
"""
Simple extractor for Lattes-like HTML (page.html -> pubs.json).

Run exactly as:
    python extract_lattes.py

This script reads `page.html` from the current working directory and writes
`pubs.json` with an array of publication objects: title, authors, place, year,
doi (null if missing) and class (one of the three target classes).
"""

import re
import json
from pathlib import Path

from bs4 import BeautifulSoup
from bs4 import NavigableString

TARGET_CLASSES = [
    "Artigos completos publicados em periódicos",
    "Capítulos de livros publicados",
    "Trabalhos completos publicados em anais de congressos",
]

SECTION_ANCHORS = {
    "Artigos completos publicados em periódicos": "ArtigosCompletos",
    "Capítulos de livros publicados": "LivrosCapitulos",
    "Trabalhos completos publicados em anais de congressos": "TrabalhosPublicadosAnaisCongresso",
}

DOI_RE = re.compile(r'''(10\.\d{4,9}/[^\s,;"'<>]+)''', re.I)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
QUOTE_RE = re.compile(r'''["“”\u201C\u201D](.+?)["“”\u201C\u201D]''')

def clean_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def is_junk_text(s: str) -> bool:
    if not s:
        return True
    low = s.lower()
    junk_keywords = [
        'ordenar por', 'var ordenacao', '#artigos-completos',
        "span[data-tipo-ordenacao", 'pagina gerada pelo sistema',
        'function(', 'return (v1', 'numerico_crescente', 'numerico:'
    ]
    for k in junk_keywords:
        if k in low:
            return True
    # extremely short or code-like
    if len(s) < 10:
        return True
    # if contains lots of code characters with few letters, treat as junk
    letters = len(re.findall(r'[A-Za-zÀ-ÖØ-öø-ÿ]', s))
    if letters / max(1, len(s)) < 0.3:
        return True
    return False


def extract_doi_from_node(node, fallback_text: str = ""):
    if node is None:
        return None
    link = node.select_one('a.icone-doi')
    if link and link.get('href'):
        href = link['href']
        doi_m = DOI_RE.search(href)
        if doi_m:
            return doi_m.group(1)
    text = fallback_text or node.get_text(" ", strip=True)
    doi_m = DOI_RE.search(text)
    if doi_m:
        return doi_m.group(1)
    return None


def find_section_header(soup: "BeautifulSoup", section_title: str):
    anchor_name = SECTION_ANCHORS.get(section_title)
    anchor = None
    if anchor_name:
        anchor = soup.find('a', {'name': anchor_name})
    if anchor:
        header = anchor
        while header and (
            getattr(header, "name", None) != "div"
            or "cita-artigos" not in (header.get("class") or [])
        ):
            header = header.parent
        if header:
            return header
    for node in soup.find_all(string=True):
        txt = (node or "").strip()
        if not txt:
            continue
        if section_title.lower() in txt.lower():
            header = node.parent
            while header and getattr(header, "name", None) != "div":
                header = header.parent
            return header
    return None


def collect_section_entries(soup: "BeautifulSoup", section_title: str) -> list:
    header = find_section_header(soup, section_title)
    if not header:
        return []
    entries = []
    cur = header.next_sibling
    while cur is not None:
        if isinstance(cur, NavigableString):
            cur = cur.next_sibling
            continue
        classes = cur.get("class") or []
        if cur.name == "div" and ("cita-artigos" in classes or "inst_back" in classes or "title-wrapper" in classes):
            break
        if cur.name in ("script", "style"):
            cur = cur.next_sibling
            continue
        span = cur.find("span", class_="transform") if hasattr(cur, "find") else None
        if span:
            text = extract_entry_text(span)
            if text and not is_junk_text(text):
                doi = extract_doi_from_node(span, text)
                entries.append((text, doi))
        cur = cur.next_sibling
    return entries


def extract_entry_text(span) -> str:
    fragment = BeautifulSoup(str(span), "html.parser")
    for info in fragment.select(".informacao-artigo"):
        info.decompose()
    return fragment.get_text(" ", strip=True)

def parse_entry_text(text: str, section_title: str) -> dict:
    t = clean_whitespace(text)
    doi_match = DOI_RE.search(t)
    doi = doi_match.group(1) if doi_match else None
    if doi_match:
        t = t.replace(doi_match.group(0), " ")

    authors = ""
    remainder = t
    author_match = re.search(r"^(.*?)\s\.\s", remainder)
    if author_match:
        authors = clean_whitespace(author_match.group(1))
        remainder = remainder[author_match.end():].strip()

    title = ""
    if remainder:
        if ". " in remainder:
            title_part, remainder = remainder.split(". ", 1)
            title = title_part.strip()
        elif "." in remainder:
            idx = remainder.find(".")
            title = remainder[:idx].strip()
            remainder = remainder[idx + 1 :].strip()
        else:
            title = remainder
            remainder = ""

    remainder = remainder.strip()
    year = ""
    year_pos = None
    matches = list(YEAR_RE.finditer(remainder))
    if matches:
        year = matches[-1].group(0)
        year_pos = matches[-1].start()
    else:
        matches = list(YEAR_RE.finditer(t))
        if matches:
            year = matches[-1].group(0)

    place = ""
    if year_pos is not None:
        place = remainder[:year_pos]
    else:
        place = remainder
    place = place.strip(" ,.;")
    if place.lower().startswith("in:"):
        place = place[3:].strip()
    if not place and remainder:
        place = remainder.strip(" ,.;")
        if place.lower().startswith("in:"):
            place = place[3:].strip()
    junk_markers = ["org.crossref"]
    lower_place = place.lower()
    for marker in junk_markers:
        idx = lower_place.find(marker)
        if idx != -1:
            place = place[:idx].strip(" ,.;")
            break

    return {
        "title": clean_whitespace(title),
        "authors": clean_whitespace(authors),
        "place": clean_whitespace(place),
        "year": str(year) if year else "",
        "doi": doi if doi else None,
        "class": section_title,
    }

def extract_with_bs4(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for cls in TARGET_CLASSES:
        entries = collect_section_entries(soup, cls)
        for text, explicit_doi in entries:
            record = parse_entry_text(text, cls)
            if explicit_doi and not record.get("doi"):
                record["doi"] = explicit_doi
            results.append(record)
    return results

def extract(html: str) -> list:
    return extract_with_bs4(html)

def main():
    src = Path('page.html')
    if not src.exists():
        print('page.html not found in current directory')
        raise SystemExit(1)
    html = src.read_text(encoding='utf-8', errors='ignore')
    items = extract(html)
    out = Path('pubs.json')
    out.write_text(json.dumps(items, ensure_ascii=False, indent=4), encoding='utf-8')
    print(f'Wrote {len(items)} items to {out}')

if __name__ == '__main__':
    main()
