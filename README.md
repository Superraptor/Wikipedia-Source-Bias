# Wikipedia Sources & Bias Analyzer

A comprehensive Python auditing toolkit to extract, analyze, and profile the bibliography and reference list of any Wikipedia article. The package resolves source-level metadata, political leanings, author demographics, readability scores, and geographic origins to produce detailed bias analysis reports and country-level geographic maps.

---

## Architecture & Workflow

The analyzer follows a multi-layered extraction pipeline:

```
[Wikipedia Page URL]
        │
        ▼
1. Citation & URL Extractor ──► Identifies Reference lists, dedups URLs
        │
        ├──────────────────────┬──────────────────────┬──────────────────────┐
        ▼                      ▼                      ▼                      ▼
2. Identifier Parser   3. Source Profiler      4. Author Profiler     5. Text Analyzer
   - DOI (Crossref)       - Domain Heuristics     - NameTrace AI         - Sentiment (HuggingFace)
   - ISBN (Wikidata)      - MBFC Live Scraping    - Wikidata (GT)        - Loaded Words Lexicon
   - OCLC (WorldCat)      - Wikidata publisher    - Type Classifier      - Readability Scores
   - Google Books ID      - Geography TLDs        - Demographics         - Wayback Fallbacks
        │                      │                      │                      │
        └──────────────────────┼──────────────────────┴──────────────────────┘
                               ▼
                    6. Aggregate Summarizer
                       - Page-Wide Distributions
                       - GeoJSON Mapping Data
                       - Text/JSON Reports
```

---

## Key Features

### 1. Geographic Auditing & Heatmap Datasets
- **Source Origins**: Maps domains using Top-Level Domains (TLD) heuristics or publisher location claims on Wikidata.
- **GeoJSON Output**: The mapping script (`map_sources.py`) outputs a FeatureCollection of points for individual sources, along with a custom `country_features` block that aggregates source counts and coordinates per country—pre-formatted for Leaflet, Mapbox, or Folium country-level heatmaps.

### 2. Author Classification & Demographics
- **Human vs Corporate Entities**: Uses the `nametrace` package or offline lexical rules to determine whether an author is a human writer or a corporate/organizational publisher.
- **Linguistic Predictors**: Estimates gender probability and regional origin using first and last name heuristics.
- **Wikidata Ground Truth (GT)**: Matches names to Wikidata Q-items to fetch precise, verified fields for gender, citizenship, political party affiliations, occupations, and employers.
- **Employer Country Mapping**: Resolves parent employer entities and maps their corresponding country of origin.

### 3. Media Bias/Fact Check (MBFC) Scraping
- Resolves publisher domains using live lookups and Wayback Machine snapshots.
- Parses exact decimal scores (e.g. `RIGHT-CENTER (4.0)`, `HIGH (1.3)`) and complete ratings (credibility, media type, country freedom rating, traffic popularity).
- Discards stale/corrupted legacy values automatically on load.

### 4. Citation Text & Readability Metrics
- **Opinion Classifier**: Flags whether citations are editorial or opinion pieces using localized multilingual loaded word lists (English, French, German, Spanish, Italian, Russian, Japanese, Portuguese, Chinese).
- **Hugging Face Sentiment Support**: Plugs into DistilBERT multilingual sentiment pipelines to compute subjectivity and sensationalism scores.
- **Flesch Readability**: Resolves Flesch Reading Ease and Flesch-Kincaid Grade Levels for the linked article text, with automatic Wayback Machine web-archive retrieval fallbacks.

### 5. Multi-Level Caching & Rate Limiting
- **Page Cache (`page_cache.json`)**: Caches complete returned profiles of pages keyed by URL and source counts to allow instantaneous subsequent executions.
- **Domain Cache (`mbfc_cache.json`)**: Caches parsed publisher ratings (including negative/empty lookups) to prevent duplicate lookups.
- **Polite Rate-Limiting**: Enforces minimum sleep delays (0.5s - 1.0s) between consecutive outgoing requests.

---

## Installation

### Prerequisites
- Python `>= 3.11`
- Optional: CUDA-enabled GPU (for faster HuggingFace sentiment pipeline processing)

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Superraptor/Wikipedia-Source-Bias.git
   cd Wikipedia-Source-Bias
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Run the test suite to verify configuration:
   ```bash
   python -m pytest -v
   ```

---

## Usage

The package exposes two primary entry points:

### 1. CommandLine Reporter (`cli.py`)
Run the CLI to generate a text report or output a raw structured JSON payload.

```bash
# Analyze the first 10 sources from a page and print a text report
python -m wikipedia_sources_bias.cli "https://fr.wikipedia.org/wiki/Emmanuel_Macron" --max-sources 10

# Analyze ALL sources on the page and save the report to a JSON file
python -m wikipedia_sources_bias.cli "https://fr.wikipedia.org/wiki/Emmanuel_Macron" --all --format json --output report.json

# Run a simplified, high-speed country-only audit (skips heavy scrapes, completes in seconds)
python -m wikipedia_sources_bias.cli "https://fr.wikipedia.org/wiki/Emmanuel_Macron" --countries-only
```

#### CLI Flags:
* `--max-sources <N>`: Maximum number of sources to analyze (default: 10).
* `--all`: Analyzes every reference on the page (overrides `--max-sources`).
* `--format [text|json]`: Sets output serialization type.
* `--countries-only`: Runs in high-speed mode, returning only domain-to-country mappings and geo-distribution percentages.
* `--no-cache`: Bypasses the local JSON page cache and forces a fresh query.
* `--output <path>`: Writes the generated report to a local text/JSON file.

---

### 2. Geographic Mapper (`map_sources.py`)
Run the mapping utility to extract coordinates for plotting sources on interactive maps.

```bash
# Generate map datasets for all sources
python -m wikipedia_sources_bias.map_sources "https://fr.wikipedia.org/wiki/Emmanuel_Macron" --all --output sources_map.json
```

---

## Detailed Report Structure

An audit report contains:
1. **Geographic Distribution**: Mapped publishing countries and regions.
2. **Political Leaning Distribution**: Ideology and bias distributions.
3. **Source Reliability Mix**: Reliability tier aggregates.
4. **Author Classification summaries**: Human vs corporate percentages, human author genders, subregions, Wikidata occupations, and employer affiliations.
5. **Language Bias Averages**: Average sensationalism, subjectivity, and opinion counts.
6. **Detailed Source Breakdown**: Comprehensive source-by-source metadata.
