from sentence_transformers import SentenceTransformer
import os

# Using the recommended BAAI/bge-small-en-v1.5
MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Cache the model instance
_model = None

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def generate_embedding(text: str) -> list[float]:
    """Generates an embedding vector for the given text."""
    model = get_embedding_model()
    # bge models recommend using 'Represent this sentence for searching relevant passages: ' 
    # for queries, but for documents we just encode them as is.
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()
