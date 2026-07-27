import os
import logging
import google.generativeai as genai
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# 🛑 PASTE YOUR GEMINI API KEY HERE
# ==========================================

load_dotenv()
GEMINI_API_KEY=os.getcwd(GOOGLE_API_KEY);
genai.configure(api_key=os.environ["GEMINI_API_KEY"])


class AyurvedicRAGPipeline:
    def __init__(self):
        # 1. Connect to Qdrant
        self.client = QdrantClient(path="qdrant_db")
        self.collection_name = "charaka_samhita"

        # 2. Load the embedding model (to understand the user's question)
        logger.info("Loading BAAI/bge-m3 embedding model...")
        self.encoder = SentenceTransformer("BAAI/bge-m3")

        # 3. Load the Gemini LLM (to generate the final answer)
        # 3. Load the Gemini LLM (Dynamically find an available model)
        logger.info("Initializing Gemini 3.5 Flash...")

        # Explicitly use the latest 3.5 model for new developer accounts
        self.llm = genai.GenerativeModel('gemini-3.5-flash')

    def retrieve_context(self, query: str, limit: int = 3) -> str:
        """Searches Qdrant and formats the retrieved verses into a single string."""
        logger.info("Searching the Charaka Samhita for relevant context...")

        query_vector = self.encoder.encode(query).tolist()

        search_results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit
        ).points

        # Compile the retrieved verses into a readable format for Gemini
        context_blocks = []
        for i, hit in enumerate(search_results, 1):
            payload = hit.payload
            block = (
                f"[Source {i}: {payload.get('book')} - {payload.get('sthana')}, "
                f"Chapter {payload.get('chapter')}, Verse {payload.get('verse')}]\n"
                f"Commentary/Meaning: {payload.get('commentary')}"
            )
            context_blocks.append(block)

        return "\n\n".join(context_blocks)

    def generate_answer(self, user_query: str):
        """The core RAG function: Retrieves context, builds the prompt, and generates the AI response."""

        # Step 1: Get the relevant ancient text (Retrieval)
        context = self.retrieve_context(user_query)

        if not context:
            print("❌ No relevant verses found in the database.")
            return

        # Step 2: Build the prompt using the context (Augmentation)
        prompt = f"""
        You are an expert Ayurvedic AI assistant specializing in the Charaka Samhita.
        A user has asked a question. You must answer their question using ONLY the provided Source Texts below.

        If the Source Texts do not contain the answer, politely state that you do not have enough information based on the current texts.
        Do not use your general internet knowledge; rely strictly on the provided commentary.

        USER QUESTION: {user_query}

        SOURCE TEXTS FROM CHARAKA SAMHITA:
        {context}

        Please provide a clear, concise, and professional answer summarizing what these specific texts say about the user's question.
        """

        # Step 3: Generate the answer (Generation)
        logger.info("Asking Gemini to synthesize the final answer...")
        response = self.llm.generate_content(prompt)

        # Print the final output beautifully
        print(f"\n{'=' * 70}")
        print(f"🌿 AI AYURVEDIC ASSISTANT")
        print(f"{'=' * 70}")
        print(f"QUESTION: {user_query}\n")
        print(f"ANSWER:\n{response.text}\n")
        print(f"{'=' * 70}\n")
        print("📚 RETRIEVED CONTEXT USED:")
        print(context)


if __name__ == "__main__":
    rag_system = AyurvedicRAGPipeline()

    # Test your completed AI!
    my_question = "What are the health benefits of Haritaki?"

    rag_system.generate_answer(my_question)