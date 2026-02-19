# news/normalizer.py
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone


# ---------------------------
# helpers
# ---------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean_text(s: Optional[str]) -> str:
    """Remove tags + collapse whitespace. Keep it short and readable."""
    if not s:
        return ""
    s = s.strip()

    # Crossref sometimes returns JATS/HTML-ish in `abstract`
    s = _TAG_RE.sub(" ", s)
    s = s.replace("\u00a0", " ")  # nbsp
    s = _WS_RE.sub(" ", s).strip()
    return s


def _first(x: Any, default: str = "") -> str:
    """Crossref often uses list fields like title/container-title."""
    if x is None:
        return default
    if isinstance(x, list):
        for it in x:
            if isinstance(it, str) and it.strip():
                return it.strip()
        return default
    if isinstance(x, str):
        return x.strip()
    return default


def _safe_int(x: Any) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(x)
    except Exception:
        return None


def _ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _parse_iso_date(s: str) -> Optional[datetime]:
    """
    Parse 'YYYY-MM-DD' or ISO datetime to aware datetime (local tz).
    """
    if not s:
        return None
    s = s.strip()
    try:
        # datetime
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            # fromisoformat may return aware if offset included
            if timezone.is_aware(dt):
                return dt.astimezone(timezone.get_current_timezone())
            return _ensure_aware(dt)
        # date
        d = date.fromisoformat(s)
        dt = datetime(d.year, d.month, d.day, 0, 0, 0)
        return _ensure_aware(dt)
    except Exception:
        return None


def _parse_pubmed_pubdate(pubdate: str) -> Tuple[Optional[datetime], Optional[int]]:
    """
    PubMed `pubdate` often like: "2018 May 15", "2020 Oct", "1999"
    Use dateutil if available; otherwise fallback to year-only.
    """
    pubdate = (pubdate or "").strip()
    if not pubdate:
        return None, None

    # Try dateutil if installed
    try:
        from dateutil import parser as dateutil_parser  # type: ignore

        dt = dateutil_parser.parse(pubdate, default=datetime(1900, 1, 1))
        # if only year exists, dateutil still makes a date — we keep it.
        return _ensure_aware(dt), dt.year
    except Exception:
        # Fallback: extract year
        m = re.search(r"(\d{4})", pubdate)
        y = int(m.group(1)) if m else None
        if y:
            dt = datetime(y, 1, 1, 0, 0, 0)
            return _ensure_aware(dt), y
        return None, None


def _hash_basis(title: str, url: str, extra: str = "") -> str:
    """
    Keep normalization side pure; hashing can also be done by your ingestion service.
    Here we just provide a stable basis string.
    """
    t = (title or "").strip().lower()
    u = (url or "").strip().lower()
    e = (extra or "").strip().lower()
    return f"{t}|{u}|{e}"


def _openalex_abstract_from_inverted_index(inv: Optional[dict]) -> str:
    """
    OpenAlex returns abstract as `abstract_inverted_index` (word -> positions).
    Reconstruct plaintext best-effort.
    """
    if not isinstance(inv, dict) or not inv:
        return ""
    try:
        max_pos = -1
        for positions in inv.values():
            if isinstance(positions, list) and positions:
                max_pos = max(max_pos, max(positions))
        if max_pos < 0:
            return ""

        words = [""] * (max_pos + 1)
        for w, positions in inv.items():
            if not isinstance(w, str) or not isinstance(positions, list):
                continue
            for p in positions:
                if isinstance(p, int) and 0 <= p <= max_pos:
                    words[p] = w

        text = " ".join([w for w in words if w])
        return _clean_text(text)
    except Exception:
        return ""


# ---------------------------
# public normalizers
# ---------------------------

def normalize_openalex_work(work: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize one OpenAlex Work object to our unified Item fields.
    OpenAlex Work object fields: title, publication_date, doi, primary_location, authorships, abstract_inverted_index. :contentReference[oaicite:2]{index=2}
    """
    title = _clean_text(work.get("title") or "")
    publication_date = work.get("publication_date") or ""
    published_at = _parse_iso_date(publication_date)

    # DOI might be in `doi` (often "https://doi.org/...") or in ids.doi
    doi = work.get("doi") or (work.get("ids") or {}).get("doi") or ""
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip() or None

    # Landing page URL: prefer primary_location.landing_page_url, fallback to any id url
    primary_location = work.get("primary_location") or {}
    url = primary_location.get("landing_page_url") or ""
    if not url:
        url = (work.get("ids") or {}).get("openalex") or ""
    url = url.strip()

    # Venue
    venue = None
    src = (primary_location.get("source") or {})
    venue = _clean_text(src.get("display_name") or "") or None

    # Authors
    authors: List[str] = []
    for a in (work.get("authorships") or [])[:50]:
        author_obj = (a or {}).get("author") or {}
        name = _clean_text(author_obj.get("display_name") or "")
        if name:
            authors.append(name)

    # Summary from inverted index (OpenAlex does not provide plaintext abstract; this is legal constraint) :contentReference[oaicite:3]{index=3}
    summary = _openalex_abstract_from_inverted_index(work.get("abstract_inverted_index"))

    year = _safe_int(work.get("publication_year"))
    if year is None and published_at:
        year = published_at.year

    # language is ISO 639-1 sometimes; keep as-is
    language = (work.get("language") or "").strip() or None

    external_id = (work.get("id") or "").strip() or None  # OpenAlex ID

    return {
        "item_type": "PAPER",
        "title": title,
        "summary": summary,
        "url": url,
        "published_at": published_at,
        "authors": authors,
        "venue": venue,
        "year": year,
        "doi": doi,
        "language": language,
        "region": None,
        "external_id": external_id,
        "hash_basis": _hash_basis(title, url, doi or external_id or ""),
        "raw": work,
    }


def normalize_crossref_work(work: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize one Crossref 'work' (usually from message.items[*]).
    Crossref REST API exposes deposited bibliographic metadata as JSON. :contentReference[oaicite:4]{index=4}
    """
    title = _clean_text(_first(work.get("title")))
    doi = (work.get("DOI") or "").strip() or None
    url = (work.get("URL") or "").strip() or ""
    if doi and not url:
        url = f"https://doi.org/{doi}"

    # Date: try issued -> published-online -> published-print -> created
    published_at = None
    for key in ("issued", "published-online", "published-print", "created"):
        obj = work.get(key)
        if isinstance(obj, dict):
            parts = obj.get("date-parts")
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                y = parts[0][0]
                m = parts[0][1] if len(parts[0]) > 1 else 1
                d = parts[0][2] if len(parts[0]) > 2 else 1
                try:
                    published_at = _ensure_aware(datetime(int(y), int(m), int(d), 0, 0, 0))
                    break
                except Exception:
                    continue

    # Authors
    authors: List[str] = []
    for a in (work.get("author") or [])[:50]:
        given = _clean_text((a or {}).get("given") or "")
        family = _clean_text((a or {}).get("family") or "")
        name = (given + " " + family).strip() if (given or family) else ""
        if name:
            authors.append(name)

    # Venue (journal / container)
    venue = _clean_text(_first(work.get("container-title"))) or None

    # Abstract if provided; otherwise empty (we do NOT scrape full text)
    summary = _clean_text(work.get("abstract") or "")
    # Optionally shorten to keep digest dense
    if len(summary) > 800:
        summary = summary[:800].rstrip() + "…"

    # year
    year = None
    if published_at:
        year = published_at.year
    else:
        year = _safe_int(work.get("published") or None)

    language = (work.get("language") or "").strip() or None

    external_id = doi  # for papers, DOI is a good stable external id

    return {
        "item_type": "PAPER",
        "title": title,
        "summary": summary,
        "url": url,
        "published_at": published_at,
        "authors": authors,
        "venue": venue,
        "year": year,
        "doi": doi,
        "language": language,
        "region": None,
        "external_id": external_id,
        "hash_basis": _hash_basis(title, url, doi or ""),
        "raw": work,
    }


def normalize_pubmed_summary(summary: Dict[str, Any], pmid: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalize one PubMed ESummary JSON entry (result[PMID]).
    In ESummary JSON, DOI may appear in `articleids` (idtype='doi') or `elocationid` like 'doi: ...'. :contentReference[oaicite:5]{index=5}
    PubMed E-utilities are the official API to Entrez/PubMed. :contentReference[oaicite:6]{index=6}
    """
    # PMID
    pmid = (pmid or summary.get("uid") or "").strip() or None

    title = _clean_text(summary.get("title") or "")

    # Authors: [{name: "..."}]
    authors: List[str] = []
    for a in (summary.get("authors") or [])[:50]:
        name = _clean_text((a or {}).get("name") or "")
        if name:
            authors.append(name)

    venue = _clean_text(summary.get("fulljournalname") or summary.get("source") or "") or None

    pubdate = (summary.get("pubdate") or "").strip()
    published_at, year = _parse_pubmed_pubdate(pubdate)

    # DOI extraction
    doi = None
    # 1) articleids
    for aid in (summary.get("articleids") or []):
        if (aid or {}).get("idtype") == "doi":
            doi = str((aid or {}).get("value") or "").strip()
            if doi:
                break

    # 2) elocationid sometimes contains "doi: ..."
    if not doi:
        eloc = str(summary.get("elocationid") or "").strip()
        if eloc.lower().startswith("doi:"):
            doi = eloc.split(":", 1)[1].strip() or None

    url = ""
    if pmid:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    elif doi:
        url = f"https://doi.org/{doi}"

    # ESummary doesn't guarantee abstract; keep summary empty (don't scrape)
    summary_text = ""

    language = None  # ESummary may not include
    external_id = pmid

    return {
        "item_type": "PAPER",
        "title": title,
        "summary": summary_text,
        "url": url,
        "published_at": published_at,
        "authors": authors,
        "venue": venue,
        "year": year,
        "doi": doi,
        "language": language,
        "region": None,
        "external_id": external_id,
        "hash_basis": _hash_basis(title, url, doi or (pmid or "")),
        "raw": summary,
    }
