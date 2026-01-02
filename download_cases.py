from datasets import load_dataset
import os
import time

# --- CONFIGURATION ---
BASE_DIR = os.path.expanduser("~/Documents/CanLaw-RAG/data/cases")
SCC_DIR = os.path.join(BASE_DIR, "scc")


def download_with_retry(builder_name, config, split, dest, retries=3):
    """Download a HuggingFace dataset with retries and longer timeout."""
    for attempt in range(1, retries + 1):
        try:
            print(f"\nAttempt {attempt} to download {builder_name}-{config}...")
            ds = load_dataset(
                builder_name,
                config,
                split=split,
                trust_remote_code=True,
            )
            ds.save_to_disk(dest)
            print(f"✅ Saved {len(ds)} examples to {dest}")
            return
        except Exception as e:
            print(f"❌ Error on attempt {attempt}: {e}")
            if attempt < retries:
                print("⏳ Waiting 10s before retrying...")
                time.sleep(10)
    print(f"❌ Failed to download {builder_name}-{config} after {retries} attempts.")


def download_cases():
    """Downloads ONLY SCC cases (Federal Court already downloaded)."""
    os.makedirs(SCC_DIR, exist_ok=True)

    print("🚀 Starting download of Canadian Legal Data (SCC only)...")

    # SCC only
    print(f"\n📥 Downloading SCC cases to: {SCC_DIR}")
    download_with_retry(
        "refugee-law-lab/canadian-legal-data",
        "SCC",
        "train",
        SCC_DIR,
    )

    print("\n🎉 Download script finished. Federal Court data was not touched.")


if __name__ == "__main__":
    download_cases()
