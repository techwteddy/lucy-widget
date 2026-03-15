from functools import lru_cache
from google import genai
from google.genai import types
from api.config import settings

MAX_CHARS = 2000
TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"
TASK_QUERY = "RETRIEVAL_QUERY"
OUTPUT_DIM = 768


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def embed(text: str, task_type: str = TASK_QUERY) -> list[float]:
    client = _get_client()
    result = await client.aio.models.embed_content(
        model=settings.embedding_model,
        contents=[text[:MAX_CHARS]],
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=OUTPUT_DIM,
        ),
    )
    return list(result.embeddings[0].values)


async def embed_batch(texts: list[str], task_type: str = TASK_DOCUMENT) -> list[list[float]]:
    client = _get_client()
    truncated = [t[:MAX_CHARS] for t in texts]
    result = await client.aio.models.embed_content(
        model=settings.embedding_model,
        contents=truncated,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=OUTPUT_DIM,
        ),
    )
    return [list(e.values) for e in result.embeddings]
