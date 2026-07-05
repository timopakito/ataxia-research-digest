import os
import xml.etree.ElementTree as ET

import requests

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

MONTHS = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


def _build_term(search_terms):
    quoted = [f'"{term}"[Title/Abstract]' for term in search_terms]
    return "(" + " OR ".join(quoted) + ")"


def _extract_date(pub_date_el):
    if pub_date_el is None:
        return None
    year = pub_date_el.findtext("Year")
    month = pub_date_el.findtext("Month", default="01")
    day = pub_date_el.findtext("Day", default="01")
    if not year:
        return None
    month = MONTHS.get(month, month).zfill(2)
    day = day.zfill(2)
    return f"{year}-{month}-{day}"


def _extract_article(article_el):
    pmid = article_el.findtext("MedlineCitation/PMID")
    title = article_el.findtext("MedlineCitation/Article/ArticleTitle") or ""
    abstract_parts = article_el.findall(
        "MedlineCitation/Article/Abstract/AbstractText"
    )
    snippet = " ".join((p.text or "") for p in abstract_parts).strip()
    pub_date_el = article_el.find(
        "MedlineCitation/Article/Journal/JournalIssue/PubDate"
    )
    date = _extract_date(pub_date_el)
    return {
        "id": pmid,
        "title": title,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "date": date,
        "source": "pubmed",
        "snippet": snippet[:600],
    }


def collect(config):
    search_terms = config["search_terms"]
    lookback_days = config["lookback_days"]
    api_key = os.environ.get("NCBI_API_KEY")

    esearch_params = {
        "db": "pubmed",
        "term": _build_term(search_terms),
        "datetype": "pdat",
        "reldate": lookback_days,
        "retmax": 100,
        "retmode": "json",
    }
    if api_key:
        esearch_params["api_key"] = api_key

    resp = requests.get(ESEARCH_URL, params=esearch_params, timeout=30)
    resp.raise_for_status()
    id_list = resp.json().get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return []

    efetch_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml",
    }
    if api_key:
        efetch_params["api_key"] = api_key

    resp = requests.get(EFETCH_URL, params=efetch_params, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    return [_extract_article(article) for article in root.findall("PubmedArticle")]
