import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("HF_ENDPOINT","https://hf-mirror.com")

import chromadb
from openai import OpenAI
from sentence_transformers import SentenceTransformer

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

CHROMA_DIR=Path("chroma_db_tuning")
REPORT_FILE=Path("rag_tuning_report.json")
MODEL_NAME="BAAI/bge-small-zh-v1.5"

print(f"加载 embedding 模型: {MODEL_NAME}")
embed_model=SentenceTransformer(MODEL_NAME)

DOCS = [
    {
        "source": "agent.txt",
        "text": (
            "Agent 的记忆分为四层。第一层是短期窗口记忆，保存最近几轮对话，"
            "直接放进上下文。第二层是摘要记忆，把旧对话压缩成一段话，保留用户身份、"
            "目标和未完成事项。第三层是结构化档案，用 JSON 保存姓名、职业、偏好等稳定事实。"
            "第四层是向量检索记忆，把历史片段和文档存入向量库，提问时按相似度召回。"
        ),
    },
    {
        "source": "rag.txt",
        "text": (
            "RAG 的完整流程是：文档加载、文本分块、向量化、存入向量库、检索、生成回答。"
            "分块参数包括 chunk_size 和 chunk_overlap。chunk_size 太大会引入无关内容，"
            "太小会把一句话切断。chunk_overlap 用于让相邻块保留上下文。"
            "检索时用 top-k 控制召回数量，用相似度阈值过滤低质量结果。"
            "回答时必须给出原文引用，减少模型幻觉。"
        ),
    },
    {
        "source": "security.txt",
        "text": (
            "提示注入是指用户诱导模型忽略原有指令的攻击方式，分为直接注入和间接注入。"
            "防御手段包括：工具最小权限、路径校验、扩展名白名单、输出脱敏、"
            "危险操作人工审批。光靠提示词无法完全防御，必须在代码层做权限控制。"
            "工具返回的内容只能当数据，不能当指令执行。"
        ),
    },
        {
        "source": "finetune.txt",
        "text": "微调是在预训练模型上用领域数据继续训练,会改变模型参数。RAG 不改变参数，只检索外部资料。数据量少、知识更新频繁时优先用 RAG;需要改变说话风格或领域语言时考虑微调。",
    },
    {
        "source": "vectordb.txt",
        "text": "向量数据库选型:Chroma 轻量、适合原型;Milvus 适合大规模生产;pgvector 适合已有 PostgreSQL 的团队;Pinecone 是全托管服务。",
    },
    {
        "source": "memory2.txt",
        "text": "短期记忆保存最近几轮对话；摘要记忆把旧对话压缩；结构化档案保存姓名和目标等稳定事实；向量记忆按相似度召回历史片段。",
    },
]

QUESTIONS = [
    {"question": "Agent 记忆的第三层是什么？", "expect_keyword": "结构化档案"},
    {"question": "数据量少、知识更新频繁时应该用 RAG 还是微调？", "expect_keyword": "RAG"},
    {"question": "大规模生产常用哪个向量数据库？", "expect_keyword": "Milvus"},
    {"question": "chunk_overlap 解决什么问题？", "expect_keyword": "重叠"},
    {"question": "公司年假有多少天？", "expect_keyword": None},
]


# encode：BGE 把文本批量转成向量；
# normalize_embeddings=True：归一化，让余弦距离有意义；
# show_progress_bar=False：不打印进度条，保持输出干净；
# .tolist()：numpy 数组 → Python 列表，Chroma 需要。
# 向量化函数
def embed(texts:list)->list:
    return embed_model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

# 分块函数

#   - 例如 size=120、overlap=20 → 每块 120 字，每次前进 100 字，相邻块重叠 20 字；
# - range(0, len(text), step)：从 0 开始，按 step 前进；
# - text[start:start+size]：切片取出这一块；
# - .strip()：去掉首尾空白；
# - if piece：跳过空块。
# 为什么需要 overlap：如果答案正好横跨两块边界，没有重叠就会被切断，两块都检索不到。
# 能得到什么：可调参数的简单分块器。真实项目会用按段落/标题的语义分块，但原理相同。
def chunk_text(text:str,size:int,overlap:int)->list:
    step=max(1,size-overlap)
    chunks=[]
    for start in range(0,len(text),step):
        piece=text[start:start+size].strip()
        if piece:
            chunks.append(piece)
    return chunks

# 建库函数
def build_kb(size:int,overlap:int):
    chunks=[]
    for doc in DOCS:
        for index,piece in enumerate(chunk_text(doc["text"],size,overlap)):
            chunks.append(
                {
                    "id":f"{doc['source']}#{index}",
                    "source":doc["source"],
                    "text":piece
                }
            )
    db=chromadb.PersistentClient(path=str(CHROMA_DIR))
    name=f"kb_{size}_{overlap}"

    try:
        db.delete_collection(name)
    except Exception:
        pass

    collection=db.get_or_create_collection(
        name=name,
        metadata={"hnsw:space":"cosine"}
    )
    collection.upsert(
        ids=[c['id'] for c in chunks],
        documents=[c['text'] for c in chunks],
        metadatas=[{"source":c['source']} for c in chunks],
        embeddings=embed([c['text'] for c in chunks])
    )
    return collection,chunks

# 检索函数（带阈值）
def search(collection,query:str,top_k:int=3,threshold: float | None=None):

    # float | None：类型注解，表示 threshold 可以是小数或者 None（Python 3.10+ 写法）；
    # n_results=top_k：先取前 k 条；
    # include：要原文、元数据、距离。
    results=collection.query(
        query_embeddings=embed([query]),
        n_results=top_k,
        include=["documents","metadatas","distances"]
    )

    hits=[]
    for doc,meta,distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        item={"text":doc,"source":meta["source"],"distance":round(float(distance),4)}
        if threshold is None or item["distance"]<threshold:
            hits.append(item)
    return hits

# 分块配置评测
# - int(True)=1，方便累加；
# # - 返回配置、块数、两个指标和明细。
# # 能得到什么：可比较不同分块参数的评测函数。
def evaluate_chunk_config(size:int,overlap:int,top_k:int =3,threshold: float=0.55):

    # 建库 → 初始化两个指标：- top1_correct：第一名是否正确；
    # - recall_at_k：正确答案是否出现在前 k 条里。
    collection,chunks=build_kb(size,overlap)
    top1_correct=0
    recall_at_k=0
    rows=[]

    for item in QUESTIONS:
        hits=search(collection,item["question"],top_k=top_k,threshold=threshold)
        keyword=item["expect_keyword"]


        #  分支 1：**无关问题场景**（预期知识库中没有相关内容）
        # - 当 `keyword` 为空时，代表这是一道 “知识库中没有答案” 的测试题
        # - `correct`：只有检索结果数量为 0 才算正确，衡量系统会不会乱召回无关内容
        # - `recalled`：和首条判断标准一致，无关问题零召回才算召回正确
        if keyword is None:
            correct=len(hits)==0
            recalled=len(hits)==0
        #   有答案问题：- top-1 包含关键词 → 正确；
        # - 前 k 条里任意一条包含 → 召回成功。
        else:
            correct=bool(hits) and keyword in hits[0]["text"]
            recalled=any(keyword in h["text"] for h in hits)
        top1_correct+=int(correct)
        recall_at_k+=int(recalled)
        rows.append(
            {
                "question": item["question"],
                "top1_correct": correct,
                "recall_at_k": recalled,
                "hits": [(h["source"], h["distance"]) for h in hits],
            }
        )
    total=len(QUESTIONS)
    return {
            "size":size,
            "overlap":overlap,
            "chunk_count":len(chunks),
            "top1_accuracy":round(top1_correct/total,3),
            "recall_at_k":round(recall_at_k/total,3),
            "rows":rows,
        }

# 阈值扫描与幻觉控制
def threshold_sweep(collection, thresholds=(0.40, 0.45, 0.50, 0.55)):
    result = []
    for threshold in thresholds:
        hit_counts = []
        top1_correct = 0
        false_positive = 0

        for item in QUESTIONS:
            hits = search(collection, item["question"], top_k=3, threshold=threshold)
            hit_counts.append(len(hits))
            keyword = item["expect_keyword"]

            if keyword is None:
                if hits:
                    false_positive = 1
            elif hits and keyword in hits[0]["text"]:
                top1_correct += 1

        result.append({
            "threshold": threshold,
            "hit_counts": hit_counts,
            "top1_correct": top1_correct,
            "top1_total": 4,
            "no_answer_false_positive": false_positive,
        })
    return result

def answer_with_context(question:str,hits:list)->str:
    context=(
        "\n".join(f"[{h['source']} {h['text']}]" for h in hits)
        if hits
        else "未检索到资料"
    )

    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role":"system","content":"你是助手，根据资料回答问题。"},
            {"role":"user","content":f"资料: {context}\n\n问题: {question}"}
        ],
        temperature=0,
        max_tokens=2000,
    )
    return response.choices[0].message.content or ""

def main():
    # - 实验 1：小分块 vs 大分块。
    small=evaluate_chunk_config(120,20)
    large=evaluate_chunk_config(300,60)
    print("\n===== 实验 1:分块参数 =====")

    for r in (small,large):
        print(
            f"size={r['size']} overlap={r['overlap']} | "
            f"chunk数={r['chunk_count']} | "
            f"top1准确率={r['top1_accuracy']:.0%} | recall@k={r['recall_at_k']:.0%}"
        )
    # 用表现更好的配置做后续实验
    if small["top1_accuracy"] >= large["top1_accuracy"]:
        best=small
    else:
        best=large
    collection,_=build_kb(best["size"],best["overlap"])
    # 实验 2：top-k
    print("\n===== 实验 2:top-k =====")
    topk_results=[]
    for k in (1,3,5):
        recall=0
        for item in QUESTIONS:
            if item["expect_keyword"] is None:
                continue
            hits=search(collection,item["question"],top_k=k,threshold=None)
            if any(item["expect_keyword"] in  h["text"] for h in hits):
                recall+=1
        recall_rate = round(recall / 3, 3)
        topk_results.append({"top_k": k, "recall": recall_rate})
        print(f"top_k={k} | recall={recall_rate:.0%}")

    # 实验 3：阈值
    print("\n===== 实验 3:相似度阈值 =====")
    thresholds=threshold_sweep(collection)
    for r in thresholds:
        print(
            f"阈值={r['threshold']} | 每题命中数={r['hit_counts']} | "
            f"无答案误召回={r['no_answer_false_positive']}"
        )

    # 实验 4：幻觉控制
    print("\n===== 实验 4:无命中时的幻觉控制 =====")
    no_answer_question = "公司年假有多少天？"

    safe_hits = search(collection, no_answer_question, top_k=3, threshold=0.55)
    safe_answer = answer_with_context(no_answer_question, safe_hits)
    print("【阈值过滤后】命中数=", len(safe_hits))
    print("回答：", safe_answer[:120])

    forced_hits = search(collection, no_answer_question, top_k=1, threshold=None)
    forced_answer = answer_with_context(no_answer_question, forced_hits)
    print("\n【强制塞入 top-1】命中数=", len(forced_hits), "距离=", forced_hits[0]["distance"] if forced_hits else None)
    print("回答：", forced_answer[:120])

    report = {
        "model": MODEL_NAME,
        "chunk_experiments": [small, large],
        "topk_experiments": topk_results,
        "threshold_experiments": thresholds,
        "hallucination": {
            "safe_hits": len(safe_hits),
            "safe_answer": safe_answer,
            "forced_hits": len(forced_hits),
            "forced_answer": forced_answer,
        },
    }
    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n报告已写入:{REPORT_FILE.resolve()}")


if __name__ == "__main__":
    main()