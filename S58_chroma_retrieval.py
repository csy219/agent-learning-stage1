from pathlib import Path

import chromadb
from sklearn.feature_extraction.text import TfidfVectorizer

CHROMA_DIR = Path("chroma_db")

DOCS = [
    {
        "id": "doc1",
        "source": "note1.txt#1",
        "text": "虚拟环境用于隔离不同项目的依赖，创建命令是 python -m venv .venv。",
    },
    {
        "id": "doc2",
        "source": "note2.txt#1",
        "text": "LangGraph 的 Checkpointer 用于保存图的状态，通过 thread_id 恢复多轮会话。",
    },
    {
        "id": "doc3",
        "source": "note3.txt#1",
        "text": "RAG 通过检索外部文档来减少模型幻觉，回答时应该给出原文引用。",
    },
    {
        "id": "doc4",
        "source": "note4.txt#1",
        "text": "提示注入是指用户诱导模型忽略原有指令的攻击方式，需要在代码层做权限控制。",
    },
]


class ChineseTfidfEmbedder:
    def __init__(self):
        # 关键修改：按“字符 n-gram”切，中文无需空格
        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 3),
            sublinear_tf=True,
        )
        self.fitted = False

    def fit(self, texts: list):
        self.vectorizer.fit(texts)
        self.fitted = True

    def embed(self, texts: list) -> list:
        if not self.fitted:
            raise RuntimeError("请先 fit")
        return self.vectorizer.transform(texts).toarray().tolist()


def build_collection():
    embedder = ChineseTfidfEmbedder()
    texts = [d["text"] for d in DOCS]
    embedder.fit(texts)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name="knowledge_v2",
        metadata={"hnsw:space": "cosine"},
    )

    collection.upsert(
        ids=[d["id"] for d in DOCS],
        documents=texts,
        metadatas=[{"source": d["source"]} for d in DOCS],
        embeddings=embedder.embed(texts),
    )

    return collection, embedder


def search(collection, embedder, query: str, top_k: int = 2) -> list:
    results = collection.query(
        query_embeddings=embedder.embed([query]),
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append(
            {
                "text": doc,
                "source": meta["source"],
                "distance": round(float(distance), 4),
            }
        )
    return hits


def main():
    collection, embedder = build_collection()

    questions = [
        "什么是虚拟环境？",
        "如何记住多轮对话？",
        "RAG 为什么能减少幻觉？",
        "提示注入怎么防？",
    ]

    for question in questions:
        print(f"\n问题:{question}")
        hits = search(collection, embedder, question, top_k=2)
        for hit in hits:
            flag = "命中" if hit["distance"] < 0.6 else "不相关"
            print(
                f"  [{flag}] 距离={hit['distance']} | "
                f"{hit['source']} | {hit['text'][:50]}"
            )


if __name__ == "__main__":
    main()