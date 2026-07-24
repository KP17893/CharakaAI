import os
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from bs4 import BeautifulSoup
import urllib3

# Suppress insecure SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure clean logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


class CharakaMasterCrawler:
    def __init__(self):
        self.base_url = "https://niimh.nic.in/ebooks/ecaraka/?mod=read"
        self.output_dir = Path("charaka_raw_html_complete")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session = self._build_session()

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

        # State tracking for the NIC server
        self.prev_sthana = 1
        self.prev_chapter = 1

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        # Aggressive retry strategy for government servers
        retry = Retry(total=5, backoff_factor=2.0, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_payload(self, sthana: int, chapter: int, adhi: str) -> dict:
        """Constructs the exact form data expected by the NIC server."""
        return {
            "scriptName": "Devanagari",
            "selSthana": str(sthana),
            "selAdhyaya": str(chapter),
            "selSthOld": str(self.prev_sthana),
            "selAdhOld": str(self.prev_chapter),
            "selAdhi": str(adhi),
            "vyaShowChecked": "checked",
            "showVya": "vyaShow",
            "footShowChecked": "checked",
            "showFoot": "vyaFoot"
        }

    def save_html(self, sthana_name: str, chapter: int, adhi: str, html_content: str):
        """Saves the HTML file with a clean, sortable filename."""
        safe_name = sthana_name.replace(" ", "_")
        filename = f"{safe_name}_Ch_{chapter:02d}_Adhi_{int(adhi):02d}.html"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

    def run(self):
        logger.info("Initializing session with NIC server...")
        try:
            self.session.get(self.base_url, timeout=30, verify=False)
        except Exception as e:
            logger.error(f"Failed initial connection: {e}")
            return

        for sthana_id, (sthana_name, total_chapters) in self.charaka_structure.items():
            for chapter_num in range(1, total_chapters + 1):
                logger.info(f"--- Processing {sthana_name} Chapter {chapter_num} ---")

                # Step 1: Request Adhi '1' to discover how many parts exist
                payload = self.get_payload(sthana_id, chapter_num, "1")

                try:
                    response = self.session.post(self.base_url, data=payload, timeout=30, verify=False)
                    response.raise_for_status()

                    # Save state for the NEXT request
                    self.prev_sthana = sthana_id
                    self.prev_chapter = chapter_num

                    # Save part 1 immediately since we already downloaded it!
                    self.save_html(sthana_name, chapter_num, "1", response.text)

                    # Parse the page to find the dropdown
                    soup = BeautifulSoup(response.text, "html.parser")
                    dropdown = soup.find("select", attrs={"name": "selAdhi"}) or soup.find("select", id="selAdhi")

                    if dropdown:
                        # Find all options except '1' (since we already saved it)
                        all_options = [opt.get("value") for opt in dropdown.find_all("option") if opt.get("value")]
                        remaining_options = [opt for opt in all_options if opt != "1"]
                        logger.info(f"Found {len(all_options)} parts. Downloading the rest...")
                    else:
                        remaining_options = []
                        logger.info("No pagination dropdown found. Assumed 1 part.")

                    # Step 2: Download the remaining parts (Adhi 2, 3, etc.)
                    for adhi_val in remaining_options:
                        time.sleep(1.5)  # Crucial: Don't hammer the server
                        payload = self.get_payload(sthana_id, chapter_num, adhi_val)

                        part_resp = self.session.post(self.base_url, data=payload, timeout=30, verify=False)
                        part_resp.raise_for_status()
                        self.save_html(sthana_name, chapter_num, adhi_val, part_resp.text)
                        logger.info(f"Saved part {adhi_val}")

                except Exception as e:
                    logger.error(f"Error processing Sthana {sthana_id} Chapter {chapter_num}: {e}")

        logger.info("🎉 Scraping Complete! All files are in 'charaka_raw_html_complete'")


if __name__ == "__main__":
    crawler = CharakaMasterCrawler()
    crawler.run()