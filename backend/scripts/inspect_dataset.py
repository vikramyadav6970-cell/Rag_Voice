"""Inspect MSMARCO-XI dataset from Hugging Face using streaming without local downloads."""

import os
import sys
import time
from typing import Any, Dict
from dotenv import load_dotenv
import fastparquet
from huggingface_hub import HfFileSystem

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")


def inspect_msmarco_xi(
    lang: str = "hin",
    split: str = "val",
    num_samples: int = 3,
) -> None:
    """Stream and inspect sample records from ai4bharat/MSMARCO-XI.

    Args:
        lang: 3-letter language code (e.g. 'hin', 'tam', 'ben', 'tel', 'mar', 'guj').
        split: 'val' or 'train'.
        num_samples: Number of sample records to inspect.
    """
    hf_token = os.getenv("HF_TOKEN")
    fs = HfFileSystem(token=hf_token)

    split_dir = "train" if split == "train" else "validation"
    parquet_path = f"datasets/ai4bharat/MSMARCO-XI/{split_dir}/{lang}{split}.parquet"

    print("=" * 70)
    print(f"INSPECTING DATASET: ai4bharat/MSMARCO-XI [{lang.upper()}, {split_dir}]")
    print(f"Remote File: {parquet_path}")
    print("=" * 70 + "\n")

    t0 = time.time()
    with fs.open(parquet_path, "rb") as f:
        pf = fastparquet.ParquetFile(f)
        total_rows = pf.count()
        print(f"Total row count for {lang} ({split_dir}): {total_rows:,} rows")
        print(f"Available schema columns ({len(pf.columns)}):\n{pf.columns}\n")

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
        # Filter available
        load_cols = [c for c in cols if c in pf.columns]
        print(f"Streaming columns: {load_cols}...")

        for df_batch in pf.iter_row_groups(columns=load_cols):
            print(f"Batch loaded in {time.time() - t0:.2f}s (Total batch size: {len(df_batch)} rows)\n")
            print("-" * 70)
            print(f"FIRST {num_samples} SAMPLES")
            print("-" * 70)

            for i in range(min(num_samples, len(df_batch))):
                row = df_batch.iloc[i].to_dict()
                print(f"\n--- Sample #{i + 1} Keys: {list(row.keys())} ---")
                print(f"Query ID     : {row.get('query_id')}")
                print(f"Query (Eng)  : {row.get('Eng_Query')}")
                print(f"Query ({lang.upper()}): {row.get('query')}")
                print(f"Answer       : {row.get('Answer')}")
                print(f"Answer (Eng) : {row.get('Eng_Answer')}")

                translated_passages = row.get("passages.Translated_passages")
                if translated_passages is not None and isinstance(translated_passages, list) and len(translated_passages) > 0:
                    print(f"Passages Count: {len(translated_passages)}")
                    print(f"Passage #1   : {str(translated_passages[0])[:180]}...")
                elif translated_passages is not None:
                    print(f"Passages     : {str(translated_passages)[:180]}...")

            print("\n" + "=" * 70)
            print("DETAILED VIEW OF SAMPLE #1 (TRUNCATED)")
            print("=" * 70)
            sample_1 = df_batch.iloc[0].to_dict()
            for k, v in sample_1.items():
                v_str = str(v)
                truncated = v_str[:220] + "..." if len(v_str) > 220 else v_str
                print(f"[{k}]: {truncated}")

            break

    print("\n" + "=" * 70)
    print("Dataset streaming & schema confirmed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    inspect_msmarco_xi(lang="hin", split="val", num_samples=3)
