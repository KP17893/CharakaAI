# 🌿 CharakaAI: Ayurvedic RAG Search Engine

An end-to-end Retrieval-Augmented Generation (RAG) pipeline designed to perform precise, cross-lingual semantic searches across the *Charaka Samhita*, one of the foundational texts of ancient Indian medicine (Ayurveda). 

This project scrapes, structures, transliterates, embeds, and indexes thousands of classical Sanskrit verses and their corresponding commentaries to provide hallucination-free, contextually accurate answers using Large Language Models (LLMs).

## Key Features
* **Resilient Web Scraping:** Custom web crawler that bypasses government (NIC) firewall rate-limits and shadow-bans to recursively extract paginated HTML data.
* **Intelligent Parsing:** Bypasses blind token-splitting by utilizing semantic structural chunking. Automatically identifies combined verses and separates chapter colophons (*Pushpika*).
* **High-Fidelity Transliteration:** Converts lossy phonetic ASCII into pristine Devanagari Unicode using `indic-transliteration` for optimal NLP context.
* **Multilingual Semantic Embeddings:** Utilizes the `BAAI/bge-m3` model (1024-dim) to map English queries to Sanskrit texts. Optimized for local hardware by resolving multi-threading tokenization deadlocks.
* **Local Vector Database:** Employs a local **Qdrant** database instance for millisecond-latency retrieval without requiring Docker or cloud hosting.
* **AI Synthesis:** Integrates **Google Gemini (3.5 Flash)** to read the retrieved ancient texts and synthesize plain-English, medically contextualized answers.

## Tech Stack
* **Language:** Python 3.x
* **AI / ML:** Google Generative AI (Gemini), `sentence-transformers` (PyTorch)
* **Database:** `qdrant-client` (Local Vector DB)
* **Data Extraction:** `BeautifulSoup4`, Regular Expressions (Regex)
* **Text Processing:** `indic-transliteration`

## Architecture Pipeline
1. **`nested_parser.py`**: Reads raw HTML, extracts verse numbers (`||X||`), handles cross-page verse merging, and transliterates text to Devanagari. Outputs structured JSON.
2. **`generate_embeddings.py`**: Loads the JSON, chunks the verses with their commentary, and generates 1024-dimensional vectors using `bge-m3`. Outputs a JSONL file.
3. **`deduplicate.py`**: A mathematical filter that cleans the dataset of phantom duplicates caused by server-side rate-limiting during the scraping phase.
4. **`populate_qdrant.py`**: Generates deterministic UUIDs and upserts the clean vectors and text payloads into a local Qdrant database folder (`qdrant_db`).
5. **`search_engine.py`**: The main user interface. Takes a natural language query, embeds it, retrieves the top 3 semantic matches from Qdrant, and prompts Gemini to generate a final answer.
