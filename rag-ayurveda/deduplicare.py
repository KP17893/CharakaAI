import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def clean_database():
    input_file = Path("embeddings/charaka_embedded.jsonl")
    output_file = Path("embeddings/charaka_embedded_clean.jsonl")

    if not input_file.exists():
        logger.error("Could not find the embedded JSONL file!")
        return

    seen_texts = set()
    duplicates_removed = 0
    clean_records = 0

    logger.info("Scanning for phantom duplicates...")

    with open(input_file, "r", encoding="utf-8") as infile, \
            open(output_file, "w", encoding="utf-8") as outfile:

        for line in infile:
            doc = json.loads(line)

            # Create a unique signature combining the Sanskrit and Commentary
            text_signature = doc.get("sanskrit", "") + doc.get("commentary", "")

            if text_signature in seen_texts:
                duplicates_removed += 1
            else:
                seen_texts.add(text_signature)
                outfile.write(line)
                clean_records += 1

    logger.info(f"🗑️ Removed {duplicates_removed} duplicate verses.")
    logger.info(f"✨ Saved {clean_records} unique, clean verses to {output_file.name}.")


if __name__ == "__main__":
    clean_database()