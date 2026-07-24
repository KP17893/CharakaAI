import json
import logging
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from pathlib import Path
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    def __init__(self):
        # Paths
        self.project_root = Path(__file__).resolve().parent.parent
        self.input_file = self.project_root / "crawler" / "parsed_json" / "charaka_samhita_nested.json"
        self.output_file = self.project_root / "crawler" / "embeddings" / "charaka_embedded.jsonl"

        # Load the BAAI/bge-m3 model.
        # sentence-transformers automatically uses GPU (CUDA/MPS) if available, otherwise CPU.
        logger.info("Loading BAAI/bge-m3 model (this may take a moment to download)...")
        self.model = SentenceTransformer("BAAI/bge-m3")

    def phonetic_to_devanagari(self, text: str) -> str:
        """Converts NIC phonetic script to Devanagari."""
        if not text:
            return ""
        clean_text = text.replace("~a", "a").replace("~", "")
        try:
            return transliterate(clean_text, sanscript.HK, sanscript.DEVANAGARI)
        except Exception:
            return text

    def flatten_and_prepare_data(self) -> List[Dict[str, Any]]:
        """Reads nested JSON, transliterates to Devanagari, and formats for embedding."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Missing input file: {self.input_file}")

        logger.info(f"Loading data from {self.input_file}")
        with open(self.input_file, "r", encoding="utf-8") as f:
            nested_data = json.load(f)

        documents = []

        # Parse the nested structure: Sthana -> Chapter -> Verses
        for sthana_name, chapters in nested_data.items():
            # Create a short code for ID generation (e.g., Sutra Sthana -> SS)
            sthana_code = "".join([word[0] for word in sthana_name.split()]).upper()

            for chapter_num_str, verses in chapters.items():
                chapter_num = int(chapter_num_str)

                for idx, verse_data in enumerate(verses, start=1):
                    # Transliterate text
                    sanskrit_dev = self.phonetic_to_devanagari(verse_data.get("sanskrit", ""))
                    commentary_dev = self.phonetic_to_devanagari(verse_data.get("commentary", ""))

                    # Generate a clean ID (e.g., CS_SS_01_001)
                    doc_id = f"CS_{sthana_code}_{chapter_num:02d}_{idx:03d}"
                    canonical_verse = verse_data.get("verse_number", str(idx))

                    # Combine texts for the embedding engine
                    embedding_text = f"Verse: {sanskrit_dev}\nCommentary: {commentary_dev}"

                    doc = {
                        "id": doc_id,
                        "book": "Charaka Samhita",
                        "sthana": sthana_name,
                        "chapter": chapter_num,
                        "verse": canonical_verse,
                        "sanskrit": sanskrit_dev,
                        "commentary": commentary_dev,
                        "embedding_text": embedding_text
                    }
                    documents.append(doc)

        logger.info(f"Flattened and prepared {len(documents)} total documents.")
        return documents

    def generate_and_save_embeddings(self):
        """Generates vectors and saves to a JSONL file."""
        documents = self.flatten_and_prepare_data()

        # Extract the texts we want to embed
        texts_to_embed = [doc["embedding_text"] for doc in documents]

        logger.info("Generating dense embeddings... (Grab a coffee, this takes time)")
        # batch_size=32 is standard. show_progress_bar gives you a nice CLI visual.
        embeddings = self.model.encode(texts_to_embed, batch_size=4, show_progress_bar=True)

        logger.info("Saving embeddings to disk...")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # Save as JSON Lines (JSONL). One JSON object per line.
        # This is highly efficient for reading row-by-row in Phase 6.
        with open(self.output_file, "w", encoding="utf-8") as f:
            for doc, emb in zip(documents, embeddings):
                # Convert numpy array to list for JSON serialization
                doc["embedding"] = emb.tolist()
                # Remove the temporary combined text to save disk space
                del doc["embedding_text"]

                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        logger.info(f"🎉 Successfully embedded and saved {len(documents)} vectors to {self.output_file}")


if __name__ == "__main__":
    generator = EmbeddingGenerator()
    generator.generate_and_save_embeddings()