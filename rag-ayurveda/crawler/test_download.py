import os
import logging
from huggingface_hub import snapshot_download

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Force HuggingFace to not use symlinks, which sometimes break in cloud environments
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

logger.info("Starting explicit download of BAAI/bge-m3...")
try:
    # We download it explicitly here. If it succeeds, it goes into the cache.
    # When your embedding script runs later, it will find it instantly.
    path = snapshot_download(
        repo_id="BAAI/bge-m3",
        resume_download=True,
        max_workers=1 # Prevents cloud thread blocking
    )
    logger.info(f"🎉 Model downloaded successfully to: {path}")
except Exception as e:
    logger.error(f"❌ Download failed: {e}")


