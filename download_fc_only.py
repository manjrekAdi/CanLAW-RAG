from datasets import load_dataset
import os

# --- CONFIGURATION ---
BASE_DIR = os.path.expanduser("~/Documents/CanLaw-RAG/data/cases")
FC_DIR = os.path.join(BASE_DIR, "federal")

def download_federal_court():
    """Downloads Federal Court cases only."""
    os.makedirs(FC_DIR, exist_ok=True)

    print("🚀 Starting download of Federal Court Cases...")
    print(f"📥 Downloading to: {FC_DIR}")

    try:
        ds = load_dataset(
            "refugee-law-lab/canadian-legal-data",
            "FC",
            split="train",
            trust_remote_code=True,
        )
        ds.save_to_disk(FC_DIR)
        print(f"\n✅ Successfully saved {len(ds)} Federal Court cases.")
        print(f"📊 Size: {os.popen(f'du -sh {FC_DIR}').read().strip()}")
    except Exception as e:
        print(f"❌ Error downloading Federal Court data: {e}")

if __name__ == "__main__":
    download_federal_court()
