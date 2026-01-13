import pandas as pd
import time
import os
from app.services.rag_pipeline import RAGPipeline
from app.core.ollama_client import query_ollama
from sentence_transformers import SentenceTransformer, util

# --- CONFIGURATION ---
# List all models you want to test here
MODELS_TO_TEST = ["qwen2.5:3b", "llama3.2:3b", "qwen2.5:7b"]

# Path to your test dataset
TEST_DATA_PATH = r"C:\Users\damie\Desktop\Projects\Python\uitm-rag-\backend\app\test_dataset.csv"

# Load scoring model once (to save time)
print("⏳ Loading Scoring Model...")
scorer_model = SentenceTransformer('all-MiniLM-L6-v2')

def evaluate_model(model_name):
    print(f"\n🚀 Starting Benchmark for Model: {model_name}")
    print("=" * 40)
    
    # 1. Validation
    if not os.path.exists(TEST_DATA_PATH):
        print(f"❌ Error: File not found at {TEST_DATA_PATH}")
        return

    # 2. Load Data
    try:
        df = pd.read_csv(TEST_DATA_PATH)
        print(f"📂 Loaded {len(df)} test cases.")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    rag = RAGPipeline()
    results = []
    
    # 3. Run Tests
    for index, row in df.iterrows():
        question = row['question']
        truth = row['ground_truth']
        
        print(f"   [{index+1}/{len(df)}] Asking: {question[:50]}...")
        
        # Retrieval Step
        context = rag.retrieve_context(question)
        
        # Prompt Construction
        if context:
            prompt = f"""
            Use this context: {context}
            Answer the user question: "{question}"
            Answer strictly based on context.
            """
        else:
            prompt = f"Answer general knowledge: {question}"
            
        # Inference Step
        start_time = time.time()
        try:
            generated_answer = query_ollama(prompt, model=model_name) 
        except Exception as e:
            generated_answer = "Error generating response"
            print(f"   ⚠️ Inference Error: {e}")
            
        duration = time.time() - start_time
        
        # Scoring Step
        embeddings = scorer_model.encode([generated_answer, truth])
        similarity_score = util.cos_sim(embeddings[0], embeddings[1]).item()
        
        results.append({
            "question": question,
            "generated_answer": generated_answer,
            "ground_truth": truth,
            "similarity_score": round(similarity_score, 4),
            "latency_seconds": round(duration, 2)
        })

    # 4. Save Results
    results_df = pd.DataFrame(results)
    
    avg_score = results_df["similarity_score"].mean()
    avg_time = results_df["latency_seconds"].mean()
    
    print("-" * 40)
    print(f"📊 SUMMARY FOR {model_name}")
    print(f"✅ Accuracy: {avg_score * 100:.2f}%")
    print(f"⏱️ Avg Time: {avg_time:.2f}s")
    print("-" * 40)
    
    # Auto-save handling
    base_filename = f"benchmark_results_{model_name.replace(':', '_')}.csv"
    
    try:
        results_df.to_csv(base_filename, index=False)
        print(f"💾 Saved to: {base_filename}")
    except PermissionError:
        timestamp = int(time.time())
        fallback = f"benchmark_results_{model_name.replace(':', '_')}_{timestamp}.csv"
        results_df.to_csv(fallback, index=False)
        print(f"💾 File locked, saved to new file: {fallback}")

if __name__ == "__main__":
    print(f"🎯 Queued {len(MODELS_TO_TEST)} models for testing...")
    
    for model in MODELS_TO_TEST:
        try:
            evaluate_model(model)
        except Exception as e:
            print(f"❌ Failed to run {model}: {e}")
            
    print("\n✅ All benchmarks completed!")