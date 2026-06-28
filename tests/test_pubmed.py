"""Tests for PubMed client."""

from src.pubmed_client import PubMedClient, PubMedArticle


SAMPLE_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
      <PMID>12345678</PMID>
      <Article PubModel="Print">
        <Journal>
          <Title>Journal of Strength and Conditioning Research</Title>
          <JournalIssue>
            <PubDate>
              <Year>2024</Year>
            </PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Effects of resistance training on muscle hypertrophy</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
          </Author>
          <Author>
            <LastName>Doe</LastName>
            <ForeName>Jane</ForeName>
          </Author>
        </AuthorList>
        <Abstract>
          <AbstractText Label="Background">This study examined resistance training.</AbstractText>
          <AbstractText Label="Results">Significant hypertrophy was observed.</AbstractText>
        </Abstract>
        <ELocationID EIdType="doi">10.1000/test</ELocationID>
      </Article>
    </MedlineCitation>
    <PubmedData/>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
      <PMID>87654321</PMID>
      <Article PubModel="Print">
        <Journal>
          <Title>Medicine and Science in Sports</Title>
          <JournalIssue>
            <PubDate>
              <Year>2023</Year>
            </PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Protein supplementation and recovery</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Brown</LastName>
            <ForeName>Alice</ForeName>
          </Author>
        </AuthorList>
        <Abstract>
          <AbstractText>Protein improves recovery after exercise.</AbstractText>
        </Abstract>
        <ELocationID EIdType="pmc">PMC123456</ELocationID>
      </Article>
    </MedlineCitation>
    <PubmedData/>
  </PubmedArticle>
</PubmedArticleSet>
"""


class TestResearchQueryDetection:
    def test_research_keywords_detected(self):
        assert PubMedClient.is_research_query("What does the research say about creatine?")
        assert PubMedClient.is_research_query("Show me clinical trials on protein timing")
        assert PubMedClient.is_research_query("Is there a study on HIIT and fat loss?")

    def test_non_research_query(self):
        assert not PubMedClient.is_research_query("What's a good bench press routine?")
        assert not PubMedClient.is_research_query("How many calories in chicken breast?")
        assert not PubMedClient.is_research_query("Log my workout: benched 185x5")


class TestSearchTermsExtraction:
    def test_extracts_meaningful_terms(self):
        terms = PubMedClient.extract_search_terms("What does research say about creatine for muscle growth?")
        assert "creatine" in terms
        assert "muscle" in terms
        assert "growth" in terms
        assert "what" not in terms

    def test_removes_stopwords(self):
        terms = PubMedClient.extract_search_terms("show me study on protein")
        assert "protein" in terms
        assert "show" not in terms

    def test_short_query_passthrough(self):
        terms = PubMedClient.extract_search_terms("creatine")
        assert terms == "creatine"


class TestXMLParsing:
    def test_parse_two_articles(self):
        articles = PubMedClient._parse_articles(SAMPLE_XML)
        assert len(articles) == 2

    def test_first_article_fields(self):
        articles = PubMedClient._parse_articles(SAMPLE_XML)
        a = articles[0]
        assert a.pmid == "12345678"
        assert "resistance training" in a.title.lower()
        assert len(a.authors) == 2
        assert a.authors[0] == "John Smith"
        assert "Journal of Strength" in a.journal
        assert a.year == "2024"
        assert a.doi == "10.1000/test"
        assert a.pmc_id is None
        assert "hypertrophy" in a.abstract.lower()

    def test_second_article_pmc(self):
        articles = PubMedClient._parse_articles(SAMPLE_XML)
        a = articles[1]
        assert a.pmid == "87654321"
        assert a.doi is None
        assert a.pmc_id == "PMC123456"
        assert len(a.authors) == 1


class TestArticleFormatting:
    def test_to_context_line_includes_pmid(self):
        article = PubMedArticle(
            pmid="12345678",
            title="Test Study",
            authors=["John Smith", "Jane Doe"],
            journal="Test Journal",
            year="2024",
            doi="10.1000/test",
            abstract="This is a test abstract about fitness.",
            pmc_id=None,
        )
        line = article.to_context_line()
        assert "Test Study" in line
        assert "PMID: 12345678" in line
        assert "John Smith" in line

    def test_to_context_line_many_authors(self):
        article = PubMedArticle(
            pmid="99999999",
            title="Large Study",
            authors=["A", "B", "C", "D", "E"],
            journal="Journal",
            year="2025",
            doi=None,
            abstract="Abstract text",
            pmc_id=None,
        )
        line = article.to_context_line()
        assert "et al." in line


class TestRetrieveContext:
    def test_non_research_query_returns_empty(self):
        client = PubMedClient()
        ctx, found = client.retrieve_context("What is a good bench press routine?")
        assert not found
        assert ctx == ""
