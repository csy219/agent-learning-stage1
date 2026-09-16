import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
# 必须在导入 sentence_transformers 之前设置镜像
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = Path("chroma_db_bge")
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
THRESHOLD = 0.6

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

print(f"加载 embedding 模型：{MODEL_NAME}（首次会下载，之后走缓存）")
model = SentenceTransformer(MODEL_NAME)


def embed(texts: list) -> list:
    """BGE 向量化:normalize 后可直接用余弦距离"""
    return model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()


def build_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name="knowledge_bge",
        metadata={"hnsw:space": "cosine"},
    )

    texts = [d["text"] for d in DOCS]
    collection.upsert(
        ids=[d["id"] for d in DOCS],
        documents=texts,
        metadatas=[{"source": d["source"]} for d in DOCS],
        embeddings=embed(texts),
    )
    return collection


def search(collection, query: str, top_k: int = 3) -> list:
    results = collection.query(
        query_embeddings=embed([query]),
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
    collection = build_collection()

    questions = [
        "什么是虚拟环境？",
        "如何记住多轮对话？",
        "RAG 为什么能减少幻觉？",
        "提示注入怎么防？",
        "公司年假有多少天？",
    ]

    for question in questions:
        print(f"\n问题:{question}")
        for hit in search(collection, question, top_k=3):
            flag = "命中" if hit["distance"] < THRESHOLD else "不相关"
            print(
                f"  [{flag}] 距离={hit['distance']} | "
                f"{hit['source']} | {hit['text'][:45]}"
            )


if __name__ == "__main__":
    main()