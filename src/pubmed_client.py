"""
PubMed API client for live biomedical literature lookups.
https://pubmed.ncbi.nlm.nih.gov / NCBI E-utilities API
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from src.config import API_TIMEOUT_SEC, LLM_RETRY_ATTEMPTS, NCBI_API_KEY
from src.retry_utils import with_retries

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
USER_AGENT = "FitZone-Chatbot/1.0 (fitness-nutrition-assistant)"

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

RESEARCH_QUERY_SIGNALS = frozenset(
    {
        "study", "studies", "research", "evidence", "science", "scientific",
        "clinical", "trial", "trials", "meta-analysis", "metaanalysis",
        "systematic", "review", "literature", "pubmed", "journal",
        "randomized", "controlled", "crossover", "cohort", "peer-reviewed",
        "peerreviewed", "abstract", "finding", "findings", "data",
        "analysis", "systematic review", "doi", "published",
    }
)

RESEARCH_STOPWORDS = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "do", "does", "did",
        "have", "has", "had", "what", "which", "who", "where", "when", "why",
        "how", "there", "their", "they", "them", "its", "it", "study", "studies",
        "research", "evidence", "science", "show", "shows", "found", "find",
        "finding", "about", "tell", "me", "you", "i", "we", "can", "could",
        "would", "should", "may", "might",
    }
)


@dataclass
class PubMedArticle:
    pmid: str
    title: str
    authors: list[str]
    journal: str
    year: str | None
    doi: str | None
    abstract: str
    pmc_id: str | None

    def to_context_line(self) -> str:
        author_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            author_str += " et al."
        parts = [f"• **{self.title}**"]
        parts.append(f"  {author_str}. *{self.journal}*")
        if self.year:
            parts[-1] += f" ({self.year})"
        if self.abstract:
            abstract_clean = self.abstract[:500].replace("\n", " ")
            parts.append(f"  Abstract: {abstract_clean}")
        parts.append(f"  PMID: {self.pmid}")
        return "\n".join(parts)


class PubMedClient:
    """Search PubMed and format article abstracts for RAG context."""

    def __init__(self, retmax: int = 3, timeout: float = API_TIMEOUT_SEC) -> None:
        self.retmax = retmax
        self.timeout = timeout

    @staticmethod
    def is_research_query(query: str) -> bool:
        tokens = set(TOKEN_PATTERN.findall(query.lower()))
        return bool(tokens & RESEARCH_QUERY_SIGNALS)

    @staticmethod
    def extract_search_terms(query: str) -> str:
        tokens = [
            token
            for token in TOKEN_PATTERN.findall(query.lower())
            if token not in RESEARCH_STOPWORDS and len(token) > 2
        ]
        if not tokens:
            return query.strip()
        return " ".join(tokens[:10])

    def search(self, search_terms: str) -> list[str]:
        params = {
            "db": "pubmed",
            "term": search_terms,
            "retmax": self.retmax,
            "retmode": "json",
            "sort": "relevance",
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        url = f"{ESEARCH_URL}?{urllib.parse.urlencode(params)}"
        payload = self._fetch_json(url)
        if not payload:
            return []
        id_list = payload.get("esearchresult", {}).get("idlist", [])
        return id_list

    def fetch_abstracts(self, pmids: list[str]) -> list[PubMedArticle]:
        if not pmids:
            return []
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        url = f"{EFETCH_URL}?{urllib.parse.urlencode(params)}"
        xml_bytes = self._fetch_bytes(url)
        if not xml_bytes:
            return []
        return self._parse_articles(xml_bytes)

    def _fetch_json(self, url: str) -> dict[str, Any] | None:
        def _request() -> dict[str, Any]:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))

        try:
            return with_retries(_request, label="pubmed_search", attempts=LLM_RETRY_ATTEMPTS)
        except RuntimeError:
            return None

    def _fetch_bytes(self, url: str) -> bytes | None:
        def _request() -> bytes:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return response.read()

        try:
            return with_retries(_request, label="pubmed_fetch", attempts=LLM_RETRY_ATTEMPTS)
        except RuntimeError:
            return None

    @staticmethod
    def _parse_articles(xml_bytes: bytes) -> list[PubMedArticle]:
        articles: list[PubMedArticle] = []
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            return []

        for article_elem in root.findall(".//PubmedArticle"):
            parsed = PubMedClient._parse_single_article(article_elem)
            if parsed is not None:
                articles.append(parsed)
        return articles

    @staticmethod
    def _parse_single_article(article_elem: ET.Element) -> PubMedArticle | None:
        try:
            medline = article_elem.find(".//MedlineCitation")
            if medline is None:
                return None

            pmid = (medline.findtext("PMID") or "").strip()
            if not pmid:
                return None

            article = medline.find(".//Article")
            if article is None:
                return None

            title = (article.findtext("ArticleTitle") or "").strip()
            if not title:
                return None

            authors: list[str] = []
            author_list = article.find(".//AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last = author.findtext("LastName") or ""
                    fore = author.findtext("ForeName") or ""
                    if last:
                        authors.append(f"{fore} {last}".strip() or last)

            journal_elem = article.find(".//Journal/Title")
            journal = (journal_elem.text if journal_elem is not None else "") or ""

            year_elem = article.find(".//Journal/JournalIssue/PubDate/Year")
            year = year_elem.text if year_elem is not None else None

            doi = None
            for eid in medline.findall(".//ELocationID"):
                if eid.get("EIdType") == "doi":
                    doi = eid.text
                    break

            abstract_parts: list[str] = []
            abstract_elem = article.find(".//Abstract")
            if abstract_elem is not None:
                for label in abstract_elem.findall("AbstractText"):
                    label_attr = label.get("Label")
                    text = (label.text or "") + "".join(
                        ET.tostring(child, encoding="unicode") for child in label
                    )
                    text = re.sub(r"<[^>]+>", "", text).strip()
                    if label_attr:
                        abstract_parts.append(f"{label_attr}: {text}")
                    else:
                        abstract_parts.append(text)

            abstract = " ".join(abstract_parts) if abstract_parts else ""
            abstract = re.sub(r"\s+", " ", abstract).strip()

            pmc_id = None
            for eid in medline.findall(".//ELocationID"):
                if eid.get("EIdType") == "pmc":
                    pmc_id = eid.text
                    break

            return PubMedArticle(
                pmid=pmid,
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                abstract=abstract[:2000],
                pmc_id=pmc_id,
            )
        except Exception:
            return None

    def retrieve_context(self, query: str) -> tuple[str, bool]:
        if not self.is_research_query(query):
            return "", False

        search_terms = self.extract_search_terms(query)
        if not search_terms:
            return "", False

        pmids = self.search(search_terms)
        if not pmids:
            return "", False

        articles = self.fetch_abstracts(pmids)
        if not articles:
            return "", False

        lines = [article.to_context_line() for article in articles]
        header = "[PUBMED RESEARCH — scientific literature relevant to your question]"
        return header + "\n" + "\n\n".join(lines), True
