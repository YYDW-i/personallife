# news/services/clients/pubmed.py
from ..http import make_session, RateLimiter
from ..normalizer import normalize_pubmed_summary
from ..dedup import url_normalize, make_content_hash

def fetch_pubmed(term: str, retmax=20):
    s = make_session()
    limiter = RateLimiter(1.0)

    # 1) ESearch 拿 PMID 列表
    limiter.wait()
    r = s.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
              params={"db":"pubmed","term":term,"retmode":"json","retmax":retmax}, timeout=10)
    r.raise_for_status()
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    # 2) ESummary 拿摘要信息（注意：不是全文）
    limiter.wait()
    r2 = s.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
               params={"db":"pubmed","id":",".join(ids),"retmode":"json"}, timeout=10)
    r2.raise_for_status()
    data = r2.json()

    items = []
    for pmid in ids:
        rec = data.get("result", {}).get(pmid)
        if not rec:
            continue
        norm = normalize_pubmed_summary(rec)
        norm["normalized_url"] = url_normalize(norm["url"])
        norm["content_hash"] = make_content_hash(norm)
        items.append(norm)
    return items
