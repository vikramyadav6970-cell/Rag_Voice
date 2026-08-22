"""Dataset Ingestion & Qdrant Indexing Script for Indic Voice RAG (HH Goa 2026).

Loads MSMARCO-XI dataset subset, applies 4 chunking strategies, computes multilingual
embeddings (bge-m3) with GPU acceleration (fp16) / CPU fallback, deduplicates passages,
and idempotently indexes vectors into Qdrant Cloud.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

# Ensure standard UTF-8 console output across Windows & Linux
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
import fastparquet
from huggingface_hub import HfFileSystem
import numpy as np
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential
import torch

# Add backend directory to sys.path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.chunking import passage_native, fixed_size, semantic, hierarchical

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_qdrant_client() -> QdrantClient:
    """Initialize authenticated Qdrant client from environment variables."""
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if not url:
        raise ValueError("QDRANT_URL is not set in backend/.env")
    return QdrantClient(url=url, api_key=api_key, timeout=45.0)


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
        print(f"Collection '{collection_name}' verified and ready.")


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


def batch_encode_with_fallback(
    model: SentenceTransformer,
    texts: List[str],
    initial_batch_size: int = 24,
) -> np.ndarray:
    """Batch embed passages with automatic CUDA OOM fallback tuning."""
    curr_batch_size = initial_batch_size

    while curr_batch_size >= 8:
        try:
            embeddings = model.encode(
                texts,
                batch_size=curr_batch_size,
                show_progress_bar=True,
                normalize_embeddings=True,
            )
            return embeddings
        except (torch.cuda.OutOfMemoryError, RuntimeError) as exc:
            err_str = str(exc).lower()
            if "out of memory" in err_str and curr_batch_size > 8:
                print(f"\n[Warning] CUDA Out of Memory with batch_size={curr_batch_size}. Clearing cache and retrying with batch_size={curr_batch_size // 2}...")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                curr_batch_size = curr_batch_size // 2
            else:
                raise

    # Final fallback to minimum batch size
    return model.encode(texts, batch_size=8, show_progress_bar=True, normalize_embeddings=True)


def run_ingest(
    languages: List[str] = ["hin"],
    split: str = "val",
    limit: int = 3000,
    collection_name: str = "msmarco_indic_rag",
    model_name: str = "BAAI/bge-m3",
    batch_size: int = 24,
    recreate: bool = False,
) -> None:
    """Execute complete end-to-end ingestion pipeline with GPU acceleration and passage deduplication."""
    start_time = time.time()
    print("=" * 70)
    print("STARTING DATASET INGESTION & QDRANT INDEXING")
    print(f"Languages: {languages} | Split: {split} | Query Limit: {limit:,}")
    print(f"Embedding Model: {model_name} | Qdrant Collection: {collection_name}")
    print("=" * 70 + "\n")

    # 1. Device Detection & Model Loading
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Device Detection] Initializing compute device: {device.upper()}")
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"  - Hardware: {gpu_name}")
        print(f"  - Available VRAM: {vram_gb:.2f} GB")
        print("  - Mode: GPU-Accelerated (Half-Precision fp16)")
    else:
        print("  - Hardware: Host CPU (torch.cuda is not active)")
        print("  - Mode: Multi-threaded CPU Fallback (Full-Precision fp32)")

    t_model_start = time.time()
    embed_model = SentenceTransformer(model_name, device=device)
    
    # Explicitly cap max sequence length to 256 tokens.
    # Justification: Our chunking strategies target 60-120 tokens per chunk (child/fixed/passage),
    # so nothing legitimate needs more than a few hundred tokens. bge-m3's default 8192 max sequence
    # length was letting a handful of long native/parent chunks balloon batch VRAM allocation and compute
    # for every batch they appeared in, causing severe slow-downs and CUDA OOMs.
    embed_model.max_seq_length = 256

    # Load model in fp16 when on CUDA for RTX 3050 VRAM optimization
    if device == "cuda":
        print("  - Converting model weights to fp16 (model.half()) for optimized VRAM footprint and 2x throughput...")
        embed_model.half()

    dim_getter = getattr(embed_model, "get_embedding_dimension", getattr(embed_model, "get_sentence_embedding_dimension", None))
    vector_size = dim_getter() if dim_getter else 1024
    print(f"Model loaded in {time.time() - t_model_start:.2f}s (Vector dimension: {vector_size}, Max Seq Length: {embed_model.max_seq_length})\n")

    # 2. Connect to Qdrant Cloud & Ensure Collection
    client = get_qdrant_client()
    ensure_collection(client, collection_name, vector_size, recreate=recreate)

    # 3. Stream and extract chunks per language
    hf_token = os.getenv("HF_TOKEN")
    fs = HfFileSystem(token=hf_token)

    total_chunks_extracted = 0
    all_raw_chunks: List[Dict[str, Any]] = []

    for lang in languages:
        split_dir = "train" if split == "train" else "validation"
        parquet_path = f"datasets/ai4bharat/MSMARCO-XI/{split_dir}/{lang}{split}.parquet"
        print(f"\n--- Loading Language Split: {lang.upper()} ({parquet_path}) ---")

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

            rows_read = 0
            for df_batch in df_iter:
                rows_to_take = min(len(df_batch), limit - rows_read)
                sub_df = df_batch.iloc[:rows_to_take]
                rows_read += len(sub_df)

                print(f"Extracted {len(sub_df):,} query rows (Total read: {rows_read:,}/{limit:,})...")

                for i in range(len(sub_df)):
                    row = sub_df.iloc[i].to_dict()
                    chunks = extract_chunks_from_record(row, language=lang, semantic_model=None)
                    all_raw_chunks.extend(chunks)

                if rows_read >= limit:
                    break

        print(f"Language {lang.upper()}: Processed {rows_read:,} queries -> {len(all_raw_chunks):,} total chunks.")

    total_chunks_extracted = len(all_raw_chunks)

    # 4. Passage Text Deduplication
    print("\n--- Deduplicating Passage & Chunk Texts ---")
    t_dedup_start = time.time()
    unique_text_map: Dict[str, str] = {}  # text_hash -> text
    chunk_hash_list: List[str] = []

    for c in all_raw_chunks:
        text = c["text"].strip()
        h = hashlib.md5(text.encode("utf-8")).hexdigest()
        chunk_hash_list.append(h)
        if h not in unique_text_map:
            unique_text_map[h] = text

    unique_hashes = list(unique_text_map.keys())
    unique_texts = [unique_text_map[h] for h in unique_hashes]
    dedup_saved_pct = (1.0 - (len(unique_texts) / max(total_chunks_extracted, 1))) * 100

    print(f"Total Chunks: {total_chunks_extracted:,}")
    print(f"Unique Texts to Embed: {len(unique_texts):,}")
    print(f"Deduplication Optimization: Saved {dedup_saved_pct:.1f}% redundant embeddings ({time.time() - t_dedup_start:.2f}s).")

    # 5. Batched Embedding Computation
    print(f"\n--- Computing Embeddings ({device.upper()} / batch_size={batch_size}) ---")
    
    # Log character length distribution of unique texts to expose outliers
    if unique_texts:
        lengths = [len(t) for t in unique_texts]
        min_len = int(np.min(lengths))
        med_len = float(np.median(lengths))
        p95_len = float(np.percentile(lengths, 95))
        max_len = int(np.max(lengths))
        print(f"Unique Text Lengths (chars): min={min_len:,} | median={med_len:.1f} | p95={p95_len:.1f} | max={max_len:,}")
        print(f"Model Max Sequence Length: {embed_model.max_seq_length} tokens (capped for fast, bounded VRAM matrix operations)")

    t_embed_start = time.time()

    embeddings = batch_encode_with_fallback(
        model=embed_model,
        texts=unique_texts,
        initial_batch_size=batch_size,
    )

    t_embed_total = time.time() - t_embed_start
    throughput = len(unique_texts) / max(t_embed_total, 0.001)
    print(f"\nEmbedding Complete:")
    print(f"  - Total Wall-Clock Embedding Time: {t_embed_total:.2f}s ({t_embed_total/60:.2f} min)")
    print(f"  - Embedding Throughput: {throughput:.2f} passages/second on {device.upper()}")

    # Map text hash to embedding vector
    embedding_cache: Dict[str, Any] = {}
    for h, emb in zip(unique_hashes, embeddings):
        embedding_cache[h] = emb.tolist() if hasattr(emb, "tolist") else list(emb)

    # 6. Build Points & Upsert to Qdrant Cloud
    print(f"\n--- Upserting {total_chunks_extracted:,} Points to Qdrant Cloud ---")
    upsert_batch_size = 100
    total_chunks_indexed = 0
    strategy_counts: Dict[str, int] = {}
    lang_counts: Dict[str, int] = {}

    for b_idx in range(0, total_chunks_extracted, upsert_batch_size):
        chunk_batch = all_raw_chunks[b_idx : b_idx + upsert_batch_size]
        hash_batch = chunk_hash_list[b_idx : b_idx + upsert_batch_size]

        points: List[models.PointStruct] = []
        for chunk_item, h in zip(chunk_batch, hash_batch):
            chunk_id = chunk_item["chunk_id"]
            strat = chunk_item["strategy"]
            lang = chunk_item["language"]
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{lang}:{chunk_id}"))

            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

            payload = {
                "text": chunk_item["text"],
                "chunk_id": chunk_id,
                "source_doc_id": chunk_item["source_doc_id"],
                "language": lang,
                "strategy": strat,
                **chunk_item["metadata"],
            }

            points.append(
                models.PointStruct(
                    id=point_uuid,
                    vector=embedding_cache[h],
                    payload=payload,
                )
            )

        upsert_batch_with_retry(client, collection_name, points)
        total_chunks_indexed += len(points)
        sys.stdout.write(f"\r  Upserted {total_chunks_indexed:,}/{total_chunks_extracted:,} points to Qdrant...")
        sys.stdout.flush()

    # 7. Final Verification and Analytics
    collection_info = client.get_collection(collection_name)
    total_points = collection_info.points_count
    total_wall_time = time.time() - start_time

    print("\n\n" + "=" * 70)
    print("INGESTION COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Compute Device Used: {device.upper()}")
    print(f"Total Wall-Clock Pipeline Time: {total_wall_time:.2f}s ({total_wall_time/60:.2f} min)")
    print(f"Embedding Phase Time: {t_embed_total:.2f}s")
    print(f"Embedding Throughput: {throughput:.2f} passages/sec")
    print(f"Total Points Ingested in this run: {total_chunks_indexed:,}")
    print(f"Total Verified Points in Qdrant '{collection_name}': {total_points:,}")
    print(f"Breakdown by Language: {lang_counts}")
    print(f"Breakdown by Strategy: {strategy_counts}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest MSMARCO-XI subset into Qdrant Cloud with GPU acceleration")
    parser.add_argument("--languages", "-l", nargs="+", default=["hin"], help="Language codes (e.g. hin tam)")
    parser.add_argument("--split", default="val", choices=["val", "train"], help="Dataset split")
    parser.add_argument("--limit", type=int, default=3000, help="Maximum number of query rows to read (default: 3000)")
    parser.add_argument("--collection", "-c", default="msmarco_indic_rag", help="Qdrant collection name")
    parser.add_argument("--model", "-m", default="BAAI/bge-m3", help="Embedding model name")
    parser.add_argument("--batch-size", "-b", type=int, default=24, help="Embedding batch size (default: 24)")
    parser.add_argument("--recreate", action="store_true", help="Recreate Qdrant collection from scratch")

    args = parser.parse_args()
    run_ingest(
        languages=args.languages,
        split=args.split,
        limit=args.limit,
        collection_name=args.collection,
        model_name=args.model,
        batch_size=args.batch_size,
        recreate=args.recreate,
    )
