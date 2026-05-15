import pandas as pd
import time
import os
import psutil # For VRAM/Memory monitoring
from app.services.rag_pipeline import RAGPipeline
from app.core.ollama_client import query_ollama
from sentence_transformers import SentenceTransformer, util

# --- CONFIGURATION ---
MODELS_TO_TEST = ["qwen2.5:3b", "llama3.2:3b", "qwen2.5:7b"]
TEST_DATA_PATH = r"C:\Users\damie\Desktop\Projects\Python\uitm-rag-\backend\app\test_dataset.csv"

print("⏳ Loading Scoring Model...")
scorer_model = SentenceTransformer('all-MiniLM-L6-v2')

def get_vram_usage():
    """Simple check for system memory usage (stand-in for dedicated VRAM tracking)"""
    return psutil.virtual_memory().percent

def evaluate_model(model_name):
    print(f"\n🚀 Starting Advanced Benchmark: {model_name}")
    print("=" * 40)
    
    df = pd.read_csv(TEST_DATA_PATH)
    rag = RAGPipeline()
    results = []
    
    for index, row in df.iterrows():
        question = row['question']
        truth = row['ground_truth']
        
        # 1. Retrieval Quality Check
        context = rag.retrieve_context(question)
        
        prompt = f"""
        Instructions: Answer strictly based on the context. If not in context, say 'I don't know'.
        Context: {context}
        Question: {question}
        """
            
        # 2. Inference & Token Counting
        start_time = time.time()
        vram_start = get_vram_usage()
        
        try:
            generated_answer = query_ollama(prompt, model=model_name) 
        except Exception as e:
            generated_answer = "Error"
            
        duration = time.time() - start_time
        vram_end = get_vram_usage()

        # 3. Calculate Advanced Metrics
        # Faithfulness: Similarity between Answer and Context (Is it grounded?)
        context_score = util.cos_sim(scorer_model.encode(generated_answer), scorer_model.encode(context)).item()
        
        # Answer Relevancy: Similarity between Answer and Question
        relevancy_score = util.cos_sim(scorer_model.encode(generated_answer), scorer_model.encode(question)).item()
        
        # Accuracy: Similarity between Answer and Ground Truth
        accuracy_score = util.cos_sim(scorer_model.encode(generated_answer), scorer_model.encode(truth)).item()

        # Token Speed Estimate (Approx. 4 chars per token)
        tps = (len(generated_answer) / 4) / duration if duration > 0 else 0
        
        results.append({
            "model": model_name,
            "accuracy": round(accuracy_score, 4),
            "faithfulness": round(context_score, 4),
            "relevancy": round(relevancy_score, 4),
            "latency": round(duration, 2),
            "tokens_per_sec": round(tps, 2),
            "mem_delta": round(vram_end - vram_start, 2)
        })

    # 4. Final Aggregation
    results_df = pd.DataFrame(results)
    avg = results_df.mean(numeric_only=True)
    
    print(f"✅ Accuracy: {avg['accuracy']*100:.1f}% | Faithfulness: {avg['faithfulness']*100:.1f}%")
    print(f"⏱️ Speed: {avg['tokens_per_sec']:.1f} tokens/sec | Avg Latency: {avg['latency']:.2f}s")
    
    results_df.to_csv(f"advanced_results_{model_name.replace(':', '_')}.csv", index=False)

if __name__ == "__main__":
    for model in MODELS_TO_TEST:
        evaluate_model(model)