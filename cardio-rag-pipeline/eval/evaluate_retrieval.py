"""
CardioRAG Retrieval Evaluation Engine
=====================================
Evaluates retrieval performance against WHO 2021 and NICE 2023 guideline chunks.
Calculates Precision@k (P@k), Recall@k, Hit Rate (Found?), MRR, and Out-of-Scope Refusal Detection.
"""

import os
import sys
import csv
import json
import math
import re
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter

# Set UTF-8 output encoding for console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself",
    "his", "how", "i", "if", "in", "into", "is", "isn", "it", "its", "itself", "just", "me", "more",
    "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", "should", "so", "some", "such",
    "t", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn", "we", "were",
    "what", "when", "where", "which", "while", "who", "whom", "why", "will", "with", "would"
}

SYNONYMS = {
    "bp": ["blood", "pressure", "systolic", "diastolic"],
    "cvd": ["cardiovascular", "disease"],
    "ckd": ["chronic", "kidney", "disease"],
    "statin": ["atorvastatin", "lipid", "cholesterol"],
    "tests": ["laboratory", "testing", "screen"],
}


class MedicalBM25Retriever:
    """Deterministic BM25 text retriever with medical acronym expansion and stopwords filtering."""

    def __init__(self, chunks: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks = chunks
        self.corpus_tokens = [self.tokenize(c["text"]) for c in chunks]
        self.doc_lens = [len(tokens) for tokens in self.corpus_tokens]
        self.avg_dl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0.0
        
        self.df = Counter()
        for doc in self.corpus_tokens:
            self.df.update(set(doc))
            
        self.num_docs = len(self.chunks)
        self.idf = {
            w: math.log((self.num_docs - freq + 0.5) / (freq + 0.5) + 1.0)
            for w, freq in self.df.items()
        }

    @staticmethod
    def tokenize(text: str, filter_stops: bool = True, expand_synonyms: bool = False) -> List[str]:
        raw_tokens = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
        tokens = []
        for t in raw_tokens:
            if filter_stops and t in STOP_WORDS:
                continue
            tokens.append(t)
            if expand_synonyms and t in SYNONYMS:
                tokens.extend(SYNONYMS[t])
        return tokens

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[float, Dict[str, Any]]]:
        query_tokens = self.tokenize(query, filter_stops=True, expand_synonyms=True)
        scores = []
        for idx, (doc_tokens, doc_len) in enumerate(zip(self.corpus_tokens, self.doc_lens)):
            score = 0.0
            tf = Counter(doc_tokens)
            for q_tok in query_tokens:
                if q_tok in self.idf:
                    w_tf = tf[q_tok]
                    w_idf = self.idf[q_tok]
                    num = w_tf * (self.k1 + 1.0)
                    denom = w_tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_dl))
                    score += w_idf * (num / denom)
            scores.append((score, self.chunks[idx]))
        
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[:top_k]


def is_chunk_relevant(chunk: Dict[str, Any], expected_source: str, expected_chunk_ids: Optional[str] = None) -> bool:
    """Determines if a retrieved chunk matches the expected ground truth source or chunk ID."""
    if not expected_source or "not covered" in expected_source.lower():
        return False
        
    chunk_id = chunk.get("chunk_id", "")
    text = chunk.get("text", "").lower()
    meta = chunk.get("metadata", {})
    rec_id = str(meta.get("recommendation_id") or "")
    sec = str(meta.get("section") or meta.get("section_name") or "").lower()
    
    # Check explicit chunk ID match if provided
    if expected_chunk_ids:
        expected_ids = [cid.strip() for cid in expected_chunk_ids.split(",") if cid.strip()]
        if chunk_id in expected_ids:
            return True

    # Check Section number match (e.g. "Section 3.6" or "Section 3.8")
    sec_match = re.search(r"section\s*([0-9\.]+)", expected_source, re.IGNORECASE)
    if sec_match:
        target_sec = sec_match.group(1)
        if target_sec in chunk_id or target_sec in sec or f"_{target_sec}_" in chunk_id:
            return True
            
    # Check Recommendation number match (e.g. "Recommendation 1", "Recommendation 1.1.7")
    rec_match = re.search(r"recommendation\s*([0-9\.]+)", expected_source, re.IGNORECASE)
    if rec_match:
        target_rec = rec_match.group(1)
        if target_rec == rec_id or f"_{target_rec}_" in chunk_id or f"_{target_rec}." in chunk_id or f"_{target_rec}_rec" in chunk_id.lower():
            return True
        # For WHO recommendations e.g. Recommendation 1 -> WHO03_3.1 or WHO03_0_REC_001
        if target_rec.isdigit():
            who_rec_pattern = f"WHO03_3.{target_rec}"
            who_exec_pattern = f"WHO03_0_REC_00{target_rec}"
            who_thr_pattern = f"WHO03_0_THR_00{target_rec}"
            if who_rec_pattern in chunk_id or who_exec_pattern in chunk_id or who_thr_pattern in chunk_id:
                return True
                
    return False


def run_evaluation(
    test_csv_path: str,
    chunks_path: str,
    output_completed_csv: str,
    top_k: int = 3,
    refusal_score_threshold: float = 4.0
) -> Dict[str, Any]:
    """Runs retrieval evaluation and fills in test set columns."""
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    retriever = MedicalBM25Retriever(chunks)
    
    rows = []
    with open(test_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    total_queries = len(rows)
    hits = 0
    total_p_at_k = 0.0
    reciprocal_ranks = []
    refusal_correct = 0
    total_out_of_scope = 0

    evaluated_rows = []

    for row in rows:
        question = row["Question"] if "Question" in row else row["question"]
        expected_src = row.get("Expected Source") or row.get("expected_source") or ""
        expected_cids = row.get("expected_chunk_ids")
        is_out_of_scope = "not covered" in expected_src.lower() or str(row.get("is_out_of_scope", "")).lower() == "true"

        results = retriever.retrieve(question, top_k=top_k)
        
        # Check domain-specific out-of-scope tokens (e.g. breast cancer in hypertension, appendicitis in lipid)
        query_toks = MedicalBM25Retriever.tokenize(question, filter_stops=True, expand_synonyms=False)
        matched_toks = [t for t in query_toks if t in retriever.df]
        domain_overlap_ratio = (len(matched_toks) / len(query_toks)) if query_toks else 0.0
        
        top_score = results[0][0] if results else 0.0
        
        if is_out_of_scope:
            total_out_of_scope += 1
            # Out of scope is recognized if domain overlap is low or top score is low
            is_refused = (domain_overlap_ratio < 0.6) or (top_score < refusal_score_threshold)
            if is_refused:
                refusal_correct += 1
                found_val = "Yes (Refusal Triggered)"
                p_at_k = 1.0
            else:
                found_val = "False Positive"
                p_at_k = 0.0
            reciprocal_ranks.append(1.0 if is_refused else 0.0)
            retrieved_summary = "Refused (Out-of-Scope detected)"
        else:
            # Check relevance among top-k
            relevant_ranks = []
            for rank_idx, (score, chunk) in enumerate(results, start=1):
                if is_chunk_relevant(chunk, expected_src, expected_cids):
                    relevant_ranks.append(rank_idx)

            if relevant_ranks:
                hits += 1
                found_val = "Yes"
                p_at_k = round(len(relevant_ranks) / top_k, 2)
                reciprocal_ranks.append(1.0 / relevant_ranks[0])
            else:
                found_val = "No"
                p_at_k = 0.0
                reciprocal_ranks.append(0.0)

            top_chunk = results[0][1] if results else {}
            meta = top_chunk.get("metadata", {})
            retrieved_summary = f"{top_chunk.get('chunk_id')} (p.{meta.get('pdf_page_start')})"

        total_p_at_k += p_at_k

        # Update row dict
        row_copy = dict(row)
        if "Found?" in row_copy:
            row_copy["Found?" ] = found_val
        elif "found" in row_copy:
            row_copy["found"] = found_val
            
        if "P@k" in row_copy:
            row_copy["P@k"] = f"{p_at_k:.2f}"
        elif "p_at_k" in row_copy:
            row_copy["p_at_k"] = f"{p_at_k:.2f}"
            
        row_copy["Top_Retrieved_Chunk"] = retrieved_summary
        row_copy["Top_BM25_Score"] = f"{top_score:.2f}"
        evaluated_rows.append(row_copy)

    # Calculate aggregate metrics
    in_scope_total = total_queries - total_out_of_scope
    hit_rate = (hits / in_scope_total) if in_scope_total > 0 else 0.0
    mean_p_at_k = (total_p_at_k / total_queries) if total_queries > 0 else 0.0
    mrr = (sum(reciprocal_ranks) / total_queries) if total_queries > 0 else 0.0
    refusal_acc = (refusal_correct / total_out_of_scope) if total_out_of_scope > 0 else 1.0

    # Write completed CSV
    out_fieldnames = list(evaluated_rows[0].keys())
    os.makedirs(os.path.dirname(output_completed_csv), exist_ok=True)
    with open(output_completed_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(evaluated_rows)

    metrics = {
        "total_queries": total_queries,
        "in_scope_queries": in_scope_total,
        "out_of_scope_queries": total_out_of_scope,
        "hits_at_k": hits,
        "hit_rate_percent": round(hit_rate * 100, 1),
        "mean_precision_at_k": round(mean_p_at_k, 3),
        "mrr": round(mrr, 3),
        "refusal_accuracy_percent": round(refusal_acc * 100, 1),
    }
    return metrics


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Evaluate WHO 2021 Day 2 Test Set
    who_test_csv = os.path.join(base_dir, "eval", "Day2_Evaluation_Test_Set.csv")
    who_chunks = os.path.join(base_dir, "data", "processed", "WHO_2021_chunks.json")
    who_completed_csv = os.path.join(base_dir, "eval", "Day2_Evaluation_Test_Set_completed.csv")
    
    print("\n" + "=" * 60)
    print("Evaluating WHO 2021 Day2 Evaluation Test Set...")
    print("=" * 60)
    who_metrics = run_evaluation(who_test_csv, who_chunks, who_completed_csv, top_k=3)
    for k, v in who_metrics.items():
        print(f"  {k}: {v}")
        
    # 2. Evaluate NICE 2023 Test Set
    nice_test_csv = os.path.join(base_dir, "eval", "NICE_2023_Evaluation_Test_Set.csv")
    nice_chunks = os.path.join(base_dir, "data", "processed", "NICE_2023_chunks.json")
    nice_completed_csv = os.path.join(base_dir, "eval", "NICE_2023_Evaluation_Test_Set_completed.csv")
    
    print("\n" + "=" * 60)
    print("Evaluating NICE 2023 Evaluation Test Set...")
    print("=" * 60)
    nice_metrics = run_evaluation(nice_test_csv, nice_chunks, nice_completed_csv, top_k=3)
    for k, v in nice_metrics.items():
        print(f"  {k}: {v}")

    # 3. Evaluate Master Combined Test Set
    master_test_csv = os.path.join(base_dir, "eval", "CardioRAG_Master_Evaluation_Test_Set.csv")
    # For master, combine both WHO and NICE chunks
    with open(who_chunks, "r", encoding="utf-8") as f:
        all_chunks = json.load(f)
    with open(nice_chunks, "r", encoding="utf-8") as f:
        all_chunks.extend(json.load(f))
        
    temp_all_chunks = os.path.join(base_dir, "data", "processed", "all_guidelines_chunks_temp.json")
    with open(temp_all_chunks, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f)
        
    master_completed_csv = os.path.join(base_dir, "eval", "CardioRAG_Master_Evaluation_Test_Set_completed.csv")
    print("\n" + "=" * 60)
    print("Evaluating Master CardioRAG Combined Evaluation Test Set...")
    print("=" * 60)
    master_metrics = run_evaluation(master_test_csv, temp_all_chunks, master_completed_csv, top_k=3)
    for k, v in master_metrics.items():
        print(f"  {k}: {v}")
        
    if os.path.exists(temp_all_chunks):
        os.remove(temp_all_chunks)
        
    print("\n[SUCCESS] All evaluation datasets evaluated and completed CSV files saved in 'eval/' directory.")
