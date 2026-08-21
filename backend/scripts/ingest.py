"""Dataset Ingestion & Qdrant Indexing Script for Indic Voice RAG.

Loads MSMARCO-XI dataset subset, applies 4 chunking strategies,
computes multilingual embeddings (bge-m3), and idempotently indexes into Qdrant Cloud.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import fastparquet
from huggingface_hub import HfFileSystem
import numpy as np
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential

# Add backend directory to sys.path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.chunking import passage_native, fixed_size, semantic, hierarchical

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_qdrant_client() -> QdrantClient:
    """Initialize authenticated Qdrant client from environment variables."""
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if not url:
        raise ValueError("QDRANT_URL is not set in backend/.env")
    return QdrantClient(url=url, api_key=api_key, timeout=30.0)


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
    recreate: bool = False,
) -> None:
    """Ensure Qdrant collection and payload indexes exist."""
    collections = client.get_collections().collections
    exists = any(c.name == collection_name for c in collections)

    if exists and recreate:
        print(f"Recreating collection '{collection_name}'...")
        client.delete_collection(collection_name)
        exists = False

    if not exists:
        print(f"Creating collection '{collection_name}' (vector size: {vector_size}, distance: COSINE)...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

        # Create payload indexes for fast filtered hybrid retrieval
        index_fields = ["language", "strategy", "source_doc_id", "parent_id", "query_id"]
        for field in index_fields:
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                print(f"  - Created payload index on '{field}'")
            except Exception as e:
                print(f"  - Note on index '{field}': {e}")
    else:
        print(f"Collection '{collection_name}' already exists.")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def upsert_batch_with_retry(
    client: QdrantClient,
    collection_name: str,
    points: List[models.PointStruct],
) -> None:
    """Idempotently upsert a batch of points into Qdrant with exponential backoff retries."""
    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True,
    )


def extract_chunks_from_record(
    row: Dict[str, Any],
    language: str,
    semantic_model: Optional[SentenceTransformer] = None,
) -> List[Dict[str, Any]]:
    """Extract passages from a dataset row and apply all 4 chunking strategies.

    Returns a flat list of chunk dictionaries with rich metadata.
    """
    query_id = str(row.get("query_id", "unknown"))
    query_text = str(row.get("query", ""))
    eng_query = str(row.get("Eng_Query", ""))
    answer_text = str(row.get("Answer", ""))

    translated_passages = row.get("passages.Translated_passages") or []
    english_passages = row.get("passages.English_passages") or []
    is_selected_flags = row.get("passages.is_selected") or []

    all_chunks: List[Dict[str, Any]] = []

    for p_idx, p_text in enumerate(translated_passages):
        if not p_text or not isinstance(p_text, str) or not p_text.strip():
            continue

        clean_passage = p_text.strip()
        doc_id = f"{query_id}_p{p_idx}"
        is_selected = bool(is_selected_flags[p_idx]) if p_idx < len(is_selected_flags) else False
        eng_passage = str(english_passages[p_idx]) if p_idx < len(english_passages) else ""

        common_meta = {
            "query_id": query_id,
            "query_text": query_text,
            "eng_query": eng_query,
            "passage_index": p_idx,
            "is_selected": is_selected,
            "eng_passage": eng_passage[:200],
            "answer_ground_truth": answer_text[:200],
        }

        # 1. Passage Native
        native_chunks = passage_native(clean_passage, doc_id, language=language, metadata=common_meta)
        all_chunks.extend(native_chunks)

        # 2. Fixed Size
        fixed_chunks = fixed_size(clean_passage, doc_id, size_tokens=120, overlap_tokens=25, language=language, metadata=common_meta)
        all_chunks.extend(fixed_chunks)

        # 3. Semantic (Sentence similarity or boundary splitting)
        sem_chunks = semantic(clean_passage, doc_id, embedding_model=semantic_model, threshold=0.65, language=language, metadata=common_meta)
        all_chunks.extend(sem_chunks)

        # 4. Hierarchical (Parent + Child linked chunks)
        hier_chunks = hierarchical(clean_passage, doc_id, child_size_tokens=60, child_overlap_tokens=15, language=language, metadata=common_meta)
        all_chunks.extend(hier_chunks)

    return all_chunks


def run_ingest(
    languages: List[str] = ["hin", "tam"],
    split: str = "val",
    max_queries_per_lang: int = 60,
    collection_name: str = "msmarco_indic_rag",
    model_name: str = "BAAI/bge-m3",
    batch_size: int = 64,
    recreate: bool = False,
) -> None:
    """Execute complete end-to-end ingestion pipeline."""
    start_time = time.time()
    print("=" * 70)
    print("STARTING DATASET INGESTION & QDRANT INDEXING")
    print(f"Languages: {languages} | Split: {split} | Queries/Lang: {max_queries_per_lang}")
    print(f"Embedding Model: {model_name} | Qdrant Collection: {collection_name}")
    print("=" * 70 + "\n")

    # 1. Initialize Hugging Face FileSystem
    hf_token = os.getenv("HF_TOKEN")
    fs = HfFileSystem(token=hf_token)

    # 2. Initialize Embedding Model
    print(f"Loading embedding model '{model_name}' (sentence-transformers)...")
    t_model_start = time.time()
    embed_model = SentenceTransformer(model_name)
    dim_getter = getattr(embed_model, "get_embedding_dimension", getattr(embed_model, "get_sentence_embedding_dimension", None))
    vector_size = dim_getter() if dim_getter else 1024
    print(f"Model loaded in {time.time() - t_model_start:.2f}s (Vector dimension: {vector_size})\n")


    # 3. Connect to Qdrant Cloud & Ensure Collection
    client = get_qdrant_client()
    ensure_collection(client, collection_name, vector_size, recreate=recreate)

    total_chunks_indexed = 0
    strategy_counts: Dict[str, int] = {}
    lang_counts: Dict[str, int] = {}

    # 4. Stream and chunk records per language
    for lang in languages:
        split_dir = "train" if split == "train" else "validation"
        parquet_path = f"datasets/ai4bharat/MSMARCO-XI/{split_dir}/{lang}{split}.parquet"
        print(f"\n--- Processing Language: {lang.upper()} ({parquet_path}) ---")

        cols = [
            "query_id",
            "query",
            "Answer",
            "Eng_Query",
            "Eng_Answer",
            "passages.Translated_passages",
            "passages.English_passages",
            "passages.is_selected",
        ]

        t_stream = time.time()
        with fs.open(parquet_path, "rb") as f:
            pf = fastparquet.ParquetFile(f)
            load_cols = [c for c in cols if c in pf.columns]
            df_iter = pf.iter_row_groups(columns=load_cols)

            df_batch = next(df_iter)
            print(f"Loaded batch of {len(df_batch)} rows in {time.time() - t_stream:.2f}s")

            # Slice to target query count
            sub_df = df_batch.iloc[:max_queries_per_lang]
            print(f"Extracting chunks across {len(sub_df)} queries...")

            lang_chunks: List[Dict[str, Any]] = []
            for i in range(len(sub_df)):
                row = sub_df.iloc[i].to_dict()
                chunks = extract_chunks_from_record(row, language=lang, semantic_model=None)
                lang_chunks.extend(chunks)

            print(f"Generated {len(lang_chunks)} chunks for {lang.upper()}.")

            # 5. Batch Embed & Upsert to Qdrant
            print(f"Embedding and upserting {len(lang_chunks)} chunks in batches of {batch_size}...")
            for b_idx in range(0, len(lang_chunks), batch_size):
                chunk_batch = lang_chunks[b_idx : b_idx + batch_size]
                texts = [c["text"] for c in chunk_batch]

                # Compute dense embeddings
                embeddings = embed_model.encode(texts, batch_size=len(texts), show_progress_bar=False, normalize_embeddings=True)

                points: List[models.PointStruct] = []
                for chunk_item, emb in zip(chunk_batch, embeddings):
                    chunk_id = chunk_item["chunk_id"]
                    point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))
                    
                    strat = chunk_item["strategy"]
                    strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

                    payload = {
                        "text": chunk_item["text"],
                        "chunk_id": chunk_id,
                        "source_doc_id": chunk_item["source_doc_id"],
                        "language": chunk_item["language"],
                        "strategy": strat,
                        **chunk_item["metadata"],
                    }

                    points.append(
                        models.PointStruct(
                            id=point_uuid,
                            vector=emb.tolist() if hasattr(emb, "tolist") else list(emb),
                            payload=payload,
                        )
                    )

                upsert_batch_with_retry(client, collection_name, points)
                total_chunks_indexed += len(points)
                sys.stdout.write(f"\r  Indexed {total_chunks_indexed} total chunks...")
                sys.stdout.flush()

    # 6. Verification and Final Metrics
    print("\n\n" + "=" * 70)
    print("INGESTION COMPLETED SUCCESSFULLY")
    print("=" * 70)
    collection_info = client.get_collection(collection_name)
    total_points = collection_info.points_count

    print(f"Total Wall-Clock Time: {time.time() - start_time:.2f} seconds")
    print(f"Total Points Ingested in this run: {total_chunks_indexed:,}")
    print(f"Total Verified Points in Qdrant '{collection_name}': {total_points:,}")
    print(f"Breakdown by Language: {lang_counts}")
    print(f"Breakdown by Strategy: {strategy_counts}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest MSMARCO-XI subset into Qdrant Cloud")
    parser.add_argument("--languages", "-l", nargs="+", default=["hin", "tam"], help="Language codes (e.g. hin tam)")
    parser.add_argument("--split", default="val", choices=["val", "train"], help="Dataset split")
    parser.add_argument("--queries", "-q", type=int, default=60, help="Number of queries per language")
    parser.add_argument("--collection", "-c", default="msmarco_indic_rag", help="Qdrant collection name")
    parser.add_argument("--model", "-m", default="BAAI/bge-m3", help="Embedding model name")
    parser.add_argument("--batch-size", "-b", type=int, default=64, help="Embedding & upsert batch size")
    parser.add_argument("--recreate", action="store_true", help="Recreate Qdrant collection from scratch")

    args = parser.parse_args()
    run_ingest(
        languages=args.languages,
        split=args.split,
        max_queries_per_lang=args.queries,
        collection_name=args.collection,
        model_name=args.model,
        batch_size=args.batch_size,
        recreate=args.recreate,
    )
