# CanLAW-RAG

A Retrieval-Augmented Generation (RAG) system for Canadian legal data, including Federal Court cases, Supreme Court of Canada (SCC) cases, and statutes.

## Project Structure

```
CanLAW-RAG/
├── data/
│   ├── cases/
│   │   ├── federal/      # Federal Court cases (63,568 cases)
│   │   └── scc/          # Supreme Court of Canada cases (15,707 cases)
│   └── statutes/
│       ├── federal/      # Federal statutes
│       └── provincial/   # Provincial statutes
├── download_cases.py     # Script to download SCC cases
├── download_fc_only.py   # Script to download Federal Court cases
├── backend/              # Backend application (to be implemented)
├── frontend/             # Frontend application (to be implemented)
├── models/               # ML models directory
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

## Data Sources

The project uses data from the [Canadian Legal Data](https://huggingface.co/datasets/refugee-law-lab/canadian-legal-data) dataset on Hugging Face:

- **Federal Court (FC)**: 63,568 cases
- **Supreme Court of Canada (SCC)**: 15,707 cases

## Setup

### Prerequisites

- Python 3.x
- `datasets` library from Hugging Face

### Installation

```bash
pip install datasets
```

### Downloading Data

To download Federal Court cases:
```bash
python download_fc_only.py
```

To download SCC cases:
```bash
python download_cases.py
```

## Data Format

Each case includes:
- Citation and citation2
- Case name
- Year
- Document date
- Language
- Unofficial text (full case text)
- Source URL
- Scraped timestamp
- Other metadata

## License

Check the original dataset license on Hugging Face.
