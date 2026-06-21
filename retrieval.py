import chromadb
import json

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="statutes")


def load_corpus(path="data/corpus.json"):
    """Load corpus.json into the ChromaDB collection. Run once (or whenever
    corpus.json changes — ChromaDB will upsert by id, so re-running is safe)."""
    with open(path) as f:
        corpus = json.load(f)

    collection.add(
        ids=[item["id"] for item in corpus],
        documents=[item["text"] for item in corpus],
        metadatas=[
            {"act": item["act"], "section": item["section"], "title": item["title"]}
            for item in corpus
        ],
    )
    print(f"Loaded {len(corpus)} sections into ChromaDB")


def retrieve_sections(query: str, n_results: int = 3) -> list[dict]:
    """Person B calls this. Interface is the contract — keep it exact."""
    results = collection.query(query_texts=[query], n_results=n_results)

    sections = []
    for i in range(len(results["ids"][0])):
        sections.append({
            "act": results["metadatas"][0][i]["act"],
            "section": results["metadatas"][0][i]["section"],
            "title": results["metadatas"][0][i]["title"],
            "text": results["documents"][0][i],
        })
    return sections


if __name__ == "__main__":
    load_corpus()

    test_queries = [
        "I'm building an online store that collects customer phone numbers and emails",
        "fintech app that processes payments and stores personal data",
        "I run a small offline shop, no website",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        for r in retrieve_sections(q):
            print(f"  → {r['act']} {r['section']}: {r['title']}")
