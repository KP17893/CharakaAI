import os
import re
import json
import logging
from collections import defaultdict
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class NestedCharakaParser:
    def __init__(self):
        self.input_dir = Path("charaka_raw_html_complete")

        self.output_dir = Path("parsed_json")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "charaka_samhita_nested.json"

        # Structure: { "Sutra Sthana": { "1": [ {sloka1}, {sloka2} ] } }
        self.nested_data = defaultdict(lambda: defaultdict(list))

    def _extract_fragmented_text(self, tag_list, prefix):
        """Sorts and joins shattered text fragments based on their ID integer."""
        fragments = [tag for tag in tag_list if tag.name == "div" and tag.get("id", "").startswith(prefix)]
        if not fragments:
            return ""
        fragments.sort(key=lambda div: int(re.search(r'\d+', div['id']).group()))
        return " ".join([f.text.strip() for f in fragments if f.text.strip()])

    def _extract_canonical_number(self, text: str, fallback_counter: int) -> str:
        """Extracts the exact verse number like ||1|| or ||1-2|| from the text."""
        # Looks for double bars containing numbers/hyphens, e.g., || 1 || or ||1-2||
        matches = re.findall(r'\|\|\s*([\d\-\s,]+)\s*\|\|', text)
        if matches:
            # Return the very last match found in the text block
            return matches[-1].strip()
        return str(fallback_counter)

    def process_chapter(self, sthana_name: str, chapter_num: int, adhi_files: list):
        """Processes all Adhi pages for a single chapter as one continuous stream."""
        logger.info(f"Stitching and parsing {sthana_name} - Chapter {chapter_num} ({len(adhi_files)} pages)")

        # 1. Combine all HTML elements from all Adhi files into one sequential list
        chapter_elements = []
        for filepath in adhi_files:
            with open(filepath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")

            for element in soup.body.descendants:
                if element.name == "hr" and "doubleLine" in element.get("class", []):
                    chapter_elements.append(element)
                elif element.name == "div" and element.get("id"):
                    if element["id"].startswith("sloka_trans_") or element["id"].startswith("vya_trans_"):
                        chapter_elements.append(element)

        # 2. Chunk the unified elements by the <hr> dividers
        chunks = []
        current_chunk = []
        for element in chapter_elements:
            if element.name == "hr":
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
            else:
                current_chunk.append(element)

        if current_chunk:
            chunks.append(current_chunk)

        # 3. Parse chunks and extract canonical verse numbers
        fallback_counter = 1
        for chunk_tags in chunks:
            sanskrit_text = self._extract_fragmented_text(chunk_tags, "sloka_trans_")
            commentary_text = self._extract_fragmented_text(chunk_tags, "vya_trans_")

            if not sanskrit_text and not commentary_text:
                continue

            # Extract the actual number from the Shloka text
            verse_number = self._extract_canonical_number(sanskrit_text, fallback_counter)

            # Save to nested structure
            verse_obj = {
                "verse_number": verse_number,
                "sanskrit": sanskrit_text,
                "commentary": commentary_text
            }

            self.nested_data[sthana_name][str(chapter_num)].append(verse_obj)
            fallback_counter += 1

    def run(self):
        if not self.input_dir.exists():
            logger.error(f"Input dir {self.input_dir} not found.")
            return

        # 1. Group files by Chapter to handle cross-page Shlokas
        # Format: { ("Sutra Sthana", 1): [file1, file2, file3] }
        chapter_groups = defaultdict(list)

        files = sorted([f for f in os.listdir(self.input_dir) if f.endswith(".html")])
        for filename in files:
            match = re.match(r"(.*)_Ch_(\d+)_Adhi_(\d+)\.html", filename)
            if match:
                sthana_name = match.group(1).replace("_", " ")
                chapter_num = int(match.group(2))
                chapter_groups[(sthana_name, chapter_num)].append(self.input_dir / filename)

        # 2. Process each chapter group
        for (sthana_name, chapter_num), adhi_files in chapter_groups.items():
            self.process_chapter(sthana_name, chapter_num, adhi_files)

        # 3. Save the nested dictionary to JSON
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.nested_data, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Successfully parsed and nested the Samhita!")
        logger.info(f"Data stored at: {self.output_file}")


if __name__ == "__main__":
    parser = NestedCharakaParser()
    parser.run()