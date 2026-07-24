import os
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CharakaPostCrawler:
    def __init__(self):
        self.base_url = "https://niimh.nic.in/ebooks/ecaraka/?mod=read"

        # Create a directory to store the downloaded HTML files
        self.output_dir = Path("charaka_raw_html")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session = self._build_session()

        # Charaka Samhita strict structure: Sthana ID -> (Name, Total Chapters)
        self.charaka_structure = {
            1: ("Sutra Sthana", 30),
            2: ("Nidana Sthana", 8),
            3: ("Vimana Sthana", 8),
            4: ("Sharira Sthana", 8),
            5: ("Indriya Sthana", 12),
            6: ("Chikitsa Sthana", 30),
            7: ("Kalpa Sthana", 12),
            8: ("Siddhi Sthana", 12)
        }

        # The server tracks what page you were previously on
        self.prev_sthana = 1
        self.prev_chapter = 1

    def _build_session(self) -> requests.Session:
        """Sets up a browser-like session with automatic retries."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })

        # Automatically retry if the government server gives a 500/503 error
        retry = Retry(total=5, backoff_factor=1.0, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def start_session(self):
        """Initializes the PHPSESSID cookie by doing a basic GET request first."""
        logger.info("Initializing session with NIC server...")
        self.session.get(self.base_url)
        time.sleep(1)

    def download_chapter(self, sthana_id: int, sthana_name: str, chapter_num: int):
        """Sends the exact POST payload to retrieve a specific chapter."""
        filename = f"{sthana_name.replace(' ', '_')}_Ch_{chapter_num:02d}.html"
        filepath = self.output_dir / filename

        # If we already downloaded it (e.g., script crashed and restarted), skip it
        if filepath.exists():
            logger.info(f"Skipping already downloaded: {filename}")
            # Update state so the next request is accurate
            self.prev_sthana = sthana_id
            self.prev_chapter = chapter_num
            return

        # The exact payload you found in the Network tab!
        payload = {
            "scriptName": "Devanagari",
            "selSthana": str(sthana_id),
            "selAdhyaya": str(chapter_num),
            "selSthOld": str(self.prev_sthana),
            "selAdhOld": str(self.prev_chapter),
            "selAdhi": "1",
            "vyaShowChecked": "checked",
            "showVya": "vyaShow",
            "footShowChecked": "checked",
            "showFoot": "vyaFoot"
        }

        logger.info(f"Fetching {sthana_name} - Chapter {chapter_num}...")

        try:
            response = self.session.post(self.base_url, data=payload, timeout=20)
            response.raise_for_status()

            # Save the raw HTML to disk
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)

            # Update previous state for the next loop
            self.prev_sthana = sthana_id
            self.prev_chapter = chapter_num

            # Wait 2 seconds to avoid overloading their server
            time.sleep(2)

        except requests.RequestException as e:
            logger.error(f"Failed to download {sthana_name} Chapter {chapter_num}: {e}")

    def run(self):
        self.start_session()

        # Loop through all 8 Sthanas
        for sthana_id, (sthana_name, total_chapters) in self.charaka_structure.items():
            # Loop through all chapters in the Sthana
            for chapter_num in range(1, total_chapters + 1):
                self.download_chapter(sthana_id, sthana_name, chapter_num)

        logger.info("🎉 All Charaka Samhita chapters downloaded successfully!")


if __name__ == "__main__":
    crawler = CharakaPostCrawler()
    crawler.run()