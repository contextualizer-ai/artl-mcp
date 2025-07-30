# API URL Testing Guide for MAM@lbl.gov

Test these URLs in your browser or with curl to see the difference email makes.

## 1. CrossRef API (Basic DOI Metadata)

### WITHOUT Email (Should work fine):
```bash
curl "https://api.crossref.org/works/10.1038/nature12373"
```

### WITH Email (Better access, rate limiting):
```bash
curl -H "Accept: application/json" \
     -H "User-Agent: ARTL-MCP/1.0 (https://github.com/contextualizer-ai/artl-mcp)" \
     -H "mailto: MAM@lbl.gov" \
     "https://api.crossref.org/works/10.1038/nature12373"
```

**Browser URLs:**
- Without email: https://api.crossref.org/works/10.1038/nature12373
- With email: https://api.crossref.org/works/10.1038/nature12373 (headers sent via curl only)

---

## 2. Unpaywall API (Open Access Info) - REQUIRES EMAIL

### WITHOUT Email (Will fail):
```bash
curl "https://api.unpaywall.org/v2/10.1038/nature12373"
```

### WITH Email (Required for access):
```bash
curl "https://api.unpaywall.org/v2/10.1038/nature12373?email=MAM@lbl.gov"
```

**Browser URLs:**
- Without email: https://api.unpaywall.org/v2/10.1038/nature12373 (should fail)
- With email: https://api.unpaywall.org/v2/10.1038/nature12373?email=MAM@lbl.gov

---

## 3. PubMed E-utilities (No email needed)

### PMIDs from DOI (Works without email):
```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=10.1038/nature12373[DOI]&retmode=json"
```

### Abstract from PMID:
```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=23851394&retmode=xml"
```

**Browser URLs:**
- DOI to PMID: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=10.1038/nature12373[DOI]&retmode=json
- Abstract: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=23851394&retmode=xml

---

## 4. CrossRef Search API

### WITHOUT Email:
```bash
curl "https://api.crossref.org/works?query=CRISPR&rows=5"
```

### WITH Email (Better rate limits):
```bash
curl -H "mailto: MAM@lbl.gov" "https://api.crossref.org/works?query=CRISPR&rows=5"
```

**Browser URLs:**
- Search: https://api.crossref.org/works?query=CRISPR&rows=5

---

## 5. NCBI ID Converter API (No email needed)

### DOI to PMCID conversion:
```bash
curl "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=artl-mcp&email=MAM@lbl.gov&ids=10.1038/nature12373&format=json"
```

### PMID to PMCID:
```bash
curl "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=artl-mcp&email=MAM@lbl.gov&ids=23851394&format=json"
```

**Browser URLs:**
- DOI to PMCID: https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=artl-mcp&email=MAM@lbl.gov&ids=10.1038/nature12373&format=json
- PMID to PMCID: https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=artl-mcp&email=MAM@lbl.gov&ids=23851394&format=json

---

## 6. OpenAlex API (No email needed)

### Paper info by DOI:
```bash
curl "https://api.openalex.org/works/https://doi.org/10.1038/nature12373"
```

**Browser URL:**
- Paper info: https://api.openalex.org/works/https://doi.org/10.1038/nature12373

---

## 7. Semantic Scholar API (No email needed)

### Paper by DOI:
```bash
curl "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1038/nature12373?fields=title,authors,citationCount,references,citations"
```

**Browser URL:**
- Paper data: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1038/nature12373?fields=title,authors,citationCount,references,citations

---

## Test Results You Should See:

### ✅ Should Work WITHOUT Email:
1. **CrossRef basic metadata** - Gets paper title, authors, journal
2. **PubMed abstracts** - Gets abstract text
3. **PubMed search** - Gets PMIDs for keywords
4. **OpenAlex** - Gets citation data
5. **Semantic Scholar** - Gets citation networks

### ❌ Should FAIL WITHOUT Email:
1. **Unpaywall API** - Returns error about missing email
2. **Enhanced CrossRef** - Works but with rate limiting

### 🚀 Should Be ENHANCED WITH Email:
1. **CrossRef with email** - Better rate limits (1000/hour vs 50/hour)
2. **Unpaywall with email** - Full access to open access detection
3. **NCBI tools with email** - Better support and rate limits

---

## Quick Browser Test:

1. **Open these in browser tabs:**
   - https://api.crossref.org/works/10.1038/nature12373
   - https://api.unpaywall.org/v2/10.1038/nature12373?email=MAM@lbl.gov
   - https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=CRISPR&retmode=json&retmax=5

2. **Compare these with curl:**
   ```bash
   # Should work
   curl "https://api.crossref.org/works/10.1038/nature12373"
   
   # Should fail without email
   curl "https://api.unpaywall.org/v2/10.1038/nature12373"
   
   # Should work with email
   curl "https://api.unpaywall.org/v2/10.1038/nature12373?email=MAM@lbl.gov"
   ```

This will help you see exactly which APIs require email vs those that work without it!