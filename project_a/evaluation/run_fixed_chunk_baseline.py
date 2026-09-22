# argparse：读取终端传给脚本的参数，例如 --chunk-size 400，还能自动生成 --help。
# json：把 eval_set.json 的文本解析成 Python 字典。
# sys：修改 Python 查找模块的路径，为后续导入 pdf_rag 做准备。
# Path：比普通字符串更适合处理文件路径，支持 / 拼接、.parent、.resolve()、.glob()。
# Any：类型提示，表示 metadata 中的值类型不固定。
# chromadb：创建和操作向量数据库。
# time，使用高精度计时器测量一次查询耗时。
# 用于计算平均值和中位数。
import argparse
import json
import sys
from pathlib import Path
from typing import Any
import time
import statistics

import chromadb


from chunking import chunk_structure_aware
from S05_2_semantic_chunking import chunk_semantic

# __file__：当前脚本自己的路径；
# Path(__file__)：转成 Path 对象；
# .resolve()：转成绝对路径并处理 ..；
# .parents[0]：当前脚本所在目录，即 evaluation；
# .parents[1]：上一级目录，即 project_a。
PROJECT_ROOT=Path(__file__).resolve().parents[1]

# my_project/          # 项目根目录
#     core/
#         validator.py
#     tools/
#         run_check.py  # 当前运行的脚本
# ```
# 1. **不加路径代码时**：`sys.path` 第一个路径是 `my_project/tools`（当前脚本目录）。
# 执行 `import core.validator` 时，Python 去 `tools` 文件夹里找 `core` 文件夹，找不到；再去标准库、第三方包目录找，也找不到，最终报错。
# 2. **加上 `sys.path.insert(0, str(PROJECT_ROOT))` 后**：
# 项目根目录 `my_project` 被插到了列表第 0 位。
# 执行 `import core.validator` 时，Python 第一个就去 `my_project` 文件夹里找，找到 `core/validator.py`，直接导入成功。
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0,str(PROJECT_ROOT))
from pdf_rag import chunk_text,embed,load_pdf_pages

COLLECTION_NAME={
    "fixed":"fixed_chunk_baseline",
    "structure":"structure_chunk_baseline",
    "semantic":"semantic_chunk_baseline"
}

# 定义参数解析函数
# parse_args 只负责把命令行参数转换成 Python 对象
def parse_args()->argparse.Namespace:
    
    # 创建参数解析器
    parser=argparse.ArgumentParser(
        description="运行固定长度分块与纯向量检索 baseline"
    )

    parser.add_argument(
        "--eval-set",
        type=Path,
        default=Path(__file__).parent / "eval_set.json",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path(__file__).parent / "corpus"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).parent / "baseline.chroma"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--chunk-mode",
        choices=["fixed","structure","semantic"],
        default="fixed"
    )
    parser.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.72
    )
    parser.add_argument("--chunk-size", type=int, default=400)
    parser.add_argument("--overlap", type=int, default=80)
    parser.add_argument("--candidate-k", type=int, default=10)
    parser.add_argument("--metric-k", type=int, default=4)
    parser.add_argument("--threshold", type=float, default=0.5)

    return parser.parse_args()

#向量化对象+分页+分块+文本向量化+入库
def index_corpus(
    corpus_dir: Path,
    db_dir: Path,
    chunk_mode:str,
    chunk_size: int,
    overlap: int,
    semantic_threshold:float
) -> tuple[chromadb.Collection, int]:
    pdf_paths = sorted(corpus_dir.glob("*.pdf"))

    if not pdf_paths:
        raise FileNotFoundError(
            f"corpus 目录中没有 PDF: {corpus_dir}"
        )

    client = chromadb.PersistentClient(path=str(db_dir))

    try:
        client.delete_collection(COLLECTION_NAME[chunk_mode])
    except (ValueError, chromadb.errors.NotFoundError):
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME[chunk_mode],
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0

    for pdf_path in pdf_paths:
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for page_number, page_text in load_pdf_pages(pdf_path):
            if chunk_mode=="fixed":
                chunks=[
                    {
                        "text":chunk,
                        "metadata":{
                            "source":pdf_path.name,
                            "page":page_number,
                            "chunk_index":chunk_index,
                            "heading":"",
                            "block_type":"fixed_window",
                            "block_index":-1
                        },
                    }
                    for chunk_index,chunk in enumerate(
                        chunk_text(
                            page_text,
                            size=chunk_size,
                         overlap=overlap
                        )
                    )
                ]
            elif chunk_mode=="structure":
                chunks=chunk_structure_aware(
                    page_text=page_text,
                    source=pdf_path.name,
                    page_number=page_number,
                    max_size=chunk_size,
                    overlap=overlap
                )
            else:
                chunks=chunk_semantic(
                    page_text=page_text,
                    source=pdf_path.name,
                    page_number=page_number,
                    max_size=chunk_size,
                    overlap=overlap,
                    similarity_threshold=semantic_threshold
                )


            for chunk in chunks:
                metadata=chunk["metadata"]
                ids.append(
                    f"{pdf_path.name}"
                    f"#p{page_number}"
                    f"#c{metadata['chunk_index']}"
                )
                documents.append(chunk["text"])
                metadatas.append(
                    {
                        "source": metadata["source"],
                        "page": metadata["page"],
                        "chunk_index": metadata["chunk_index"],
                        "heading":metadata["heading"],
                        "block_type":metadata.get("block_type","unknown"),
                        "block_index":metadata.get("block_index",-1),
                        "semantic_group_size":metadata.get("semantic_group_size",1),
                        "block_indices":metadata.get("block_indices","")
                    }
                )

        if ids:
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embed(documents),
            )
            total_chunks += len(ids)

        print(f"indexed {pdf_path.name}: {len(ids)} chunks")

    return collection, total_chunks
        

# 单例检索
def query_hits(
        collection:chromadb.Collection,
        question:str,
        candidate_k:int
)->tuple[list[dict[str,Any]],float]:
    start=time.perf_counter()

    result = collection.query(
        query_embeddings=embed([question]),
        n_results=candidate_k,
        include=["documents","metadatas","distances"]
    )

    latency_ms=(time.perf_counter()-start)*1000

    hits:list[dict[str,Any]]=[]

    for document,metadata,distance in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0]
    ):
        hits.append(
            {
                "source":metadata["source"],
                "page":metadata["page"],
                "chunk_index":metadata["chunk_index"],
                "distance":round(float(distance),4),
                "text":document
            }
        )
    return hits,latency_ms

# `expected_ranks`：工具函数，计算「标准答案来源」在检索结果里的排名
def expected_ranks(
        hits:list[dict[str,Any]],
        expected_sources:list[dict[str,Any]],
)->list[int | None]:
    ranks: list[int | None] = []

    for expected in expected_sources:
        rank=None

        for hit_index,hit in enumerate(hits,start=1):
            if(
                hit["source"]==expected["source"]
                and hit["page"]==expected["page"]
            ):
                rank=hit_index
                break
        ranks.append(rank)
    return ranks


# `evaluate_case`：单题完整评测主函数，完成「检索→过滤→判分→结构化输出」全流程\
def evaluate_case(
        collection:chromadb.Collection,
        case:dict[str,Any],
        candidate_k:int,
        metric_k:int,
        threshold:float
)->dict[str,Any]:
    hits,latency_ms=query_hits(
        collection=collection,
        question=case["question"],
        candidate_k=candidate_k
    )

    filtered_hits=[hit for hit in hits if hit["distance"]<threshold]

    top_metric_hits=hits[:metric_k]
    ranks=expected_ranks(
        hits=top_metric_hits,
        expected_sources=case["expected_sources"]
    )

    source_check=case["source_check"]

    # none any all

    if source_check=="none":
        if "injection" in case["category"]:
            retrieval_ok=True
        else:
            retrieval_ok=not filtered_hits

    elif source_check=="any":
        retrieval_ok=any(rank is not None for rank in ranks)
    elif source_check=="all":
        retrieval_ok=bool(ranks) and all(rank is not None for rank in ranks)
    else:
        raise ValueError(
            f"{case['id']}: 未知source_check={source_check}"
        )

    # **倒数排名（Reciprocal Rank）」这个精细评分指标**，
    reciprocal_rank=0.0
    found_ranks=[rank for rank in ranks if rank is not None]
    if found_ranks:
        reciprocal_rank=1.0/min(found_ranks)

    return {
        "id":case["id"],
        "category":case["category"],
        "question":case["question"],
        "source_check":source_check,
        "retrieval_ok":retrieval_ok,
        "expected_sources":case["expected_sources"],
        "ranks":ranks,
        "reciprocal_rank":round(reciprocal_rank,4),
        "latency_ms":round(latency_ms,2),
        "hits":[
            {
                "source":hit["source"],
                "page":hit["page"],
                "distance":hit["distance"]
            }
            for hit in hits
        ],
    }
# 安全的平均值函数。空列表时返回 0.0，避免除以零
def safe_mean(values:list[float])->float:
    return statistics.mean(values) if values else 0.0

# 把逐题结果汇总成整体指标。
def build_summary(
        rows:list[dict[str,Any]],
        metric_k:int
)->dict[str,Any]:
    # `total`：总评测题数，
    # `retrieval_passed`：检索通过的题目总数
    total=len(rows)
    retrieval_passed=sum(1 for row in rows if row["retrieval_ok"])

    ### . 筛选有效统计样本
    # 筛选出**有标准答案来源**的题目，排除掉 `none` 类型的无答案题、注入题。
    # - 原因：命中率、召回率、MRR 这些检索质量指标，只能在「有标准答案」的题目上计算；把无答案题算进分母会导致指标失真。
    cases_with_sources=[
        row for row in rows if row["expected_sources"]
    ]

    # 倒数排名收集
    reciprocal_ranks=[
        row["reciprocal_rank"] for row in cases_with_sources
    ]


    # 首名命中数（Hit@1）
    first_hit_count=sum(
        any(rank==1 for rank in row["ranks"])
        for row in cases_with_sources
    )

    # Top-K 题目命中数（Hit@K，题目级） 
    metric_hit_count=sum(
        any(
            rank is not None and rank <=metric_k
            for rank in row["ranks"]
        )
        for row in cases_with_sources
    )

    # 标准答案总量与命中量（点级）
    expected_total=sum(
        len(row["expected_sources"])
        for row in cases_with_sources
    )

    expected_found=sum(
        sum(
            rank is not None and rank<=metric_k
            for rank in row["ranks"]
        )
        for row in cases_with_sources
    )

    latencies=[row["latency_ms"] for row in rows]

    return {
        "cases":total,
        "retrieval_passed":retrieval_passed,
        "retrieval_accuracy":round(retrieval_passed/total,4),
        "cases_with_expected_sources":len(cases_with_sources),
        "hit_at_1":round(first_hit_count/len(cases_with_sources),4),
        "hit_at_metric_k":round(metric_hit_count/len(cases_with_sources),4),
        "recall_at_metric_k":round(expected_found/expected_total,4),
        "mrr":round(safe_mean(reciprocal_ranks),4),
        "latency_ms_avg":round(safe_mean(latencies),2),
        "latency_ms_p50":round(statistics.median(latencies),2),
        "latency_ms_max":round(max(latencies),2)
    }


        
    

def main()->int:
    args=parse_args()

    document=json.loads(
        args.eval_set.read_text(encoding="utf-8")
    )
    cases=document.get("cases",[])

    if not cases:
        raise ValueError("eval_set.json中没有cases")
    
    collection,total_chunks=index_corpus(
        corpus_dir=args.corpus,
        db_dir=args.db,
        chunk_mode=args.chunk_mode,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        semantic_threshold=args.semantic_threshold
    )

    rows=[
        evaluate_case(
            collection=collection,
            case=case,
            candidate_k=args.candidate_k,
            metric_k=args.metric_k,
            threshold=args.threshold
        )
        for case in cases
    ]


    summary=build_summary(
        rows=rows,
        metric_k=args.metric_k
    )

    report={
        # ① config：实验配置区
        "config":{
            "chunk_mode":args.chunk_mode,
            "chunk_size":args.chunk_size,
            "overlap":args.overlap,
            "candidate_k":args.candidate_k,
            "metric_k":args.metric_k,
            "threshold":args.threshold,
            "semantic_threshold":args.semantic_threshold,
            "embeddings_model":"BAAI/bge-small-zh-v1.5",
            "retrieval":"vector_only"
        },
        # ② index：索引信息区
        "index":{
            "collection":COLLECTION_NAME[args.chunk_mode],
            "total_chunks":total_chunks,
        },
        # ③ summary：汇总指标区
        "summary":summary,
        # ④ rows：单题详情区
        "rows":rows
    }

    output_path=args.output
    if output_path is None:
        output_path=(
            Path(__file__).parent
            / "reports"
            /f"{args.chunk_mode}_chunk_baseline.json"
        )

    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(
        json.dumps(report,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

    print("\n===== Fixed Chunk Baseline =====")
    for key,value in summary.items():
        print(f"{key}:{value}")
    print(f"report: {output_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


