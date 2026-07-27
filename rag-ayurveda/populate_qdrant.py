import json
import uuid
import logging
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class QdrantPopulator:
    def __init__(self):
        self.input_file = Path("embeddings/charaka_embedded_clean.jsonl")

        # This creates a local database folder named "qdrant_db" right in your project.
        # No servers or Docker needed for local development!
        self.db_path = Path("qdrant_db")
        self.client = QdrantClient(path=str(self.db_path))
        self.collection_name = "charaka_samhita"

        # BAAI/bge-m3 produces vectors with exactly 1024 dimensions
        self.vector_size = 1024

    def setup_collection(self):
        """Creates a fresh collection, overwriting if it already exists."""
        if self.client.collection_exists(self.collection_name):
            logger.info(f"Collection '{self.collection_name}' already exists. Recreating it...")
            self.client.delete_collection(self.collection_name)

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
        )
        logger.info(f"✅ Collection '{self.collection_name}' is ready.")

    def generate_uuid(self, string_id: str) -> str:
        """Qdrant requires UUIDs. We generate a deterministic UUID based on our CS_SS_01_001 string."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, string_id))

    def upload_data(self):
        if not self.input_file.exists():
            logger.error(f"Cannot find embeddings file at {self.input_file}")
            return

        self.setup_collection()

        points_batch = []
        batch_size = 200  # Upload in batches of 200 to keep memory low
        total_uploaded = 0

        logger.info("Starting upload to Qdrant...")

        # Read the JSONL file line by line
        with open(self.input_file, "r", encoding="utf-8") as f:
            for line in f:
                doc = json.loads(line)

                vector = doc.pop("embedding")
                doc_id = doc["id"]

                # Create the Qdrant Point
                point = PointStruct(
                    id=self.generate_uuid(doc_id),
                    vector=vector,
                    payload=doc  # Metadata (Sthana, chapter, sanskrit, commentary, etc.)
                )
                points_batch.append(point)

                # Upload when batch is full
                if len(points_batch) >= batch_size:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points_batch
                    )
                    total_uploaded += len(points_batch)
                    logger.info(f"Uploaded {total_uploaded} verses...")
                    points_batch = []  # Reset batch

        # Upload any remaining points
        if points_batch:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points_batch
            )
            total_uploaded += len(points_batch)

        logger.info(f"🎉 Successfully indexed all {total_uploaded} verses into Qdrant!")


if __name__ == "__main__":
    populator = QdrantPopulator()
    populator.upload_data()