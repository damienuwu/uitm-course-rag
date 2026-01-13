import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

def generate_comparison_graph():
    # 1. Find all benchmark result CSV files
    # Looks for files starting with 'benchmark_results_' and ending in '.csv'
    csv_files = glob.glob("benchmark_results_*.csv")
    
    if not csv_files:
        print("❌ No benchmark result files found! Run benchmark.py first.")
        return

    model_names = []
    accuracies = []
    latencies = []

    print(f"📊 Found {len(csv_files)} result files. Generating graph...")

    # 2. Read data from each file
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            
            # Extract Model Name from filename (e.g., 'benchmark_results_qwen2.5_3b.csv' -> 'qwen2.5:3b')
            # Removes prefix and suffix for cleaner label
            name = file.replace("benchmark_results_", "").replace(".csv", "").replace("_", ":")
            
            # Calculate Averages
            avg_acc = df["similarity_score"].mean() * 100 # Convert to %
            avg_lat = df["latency_seconds"].mean()
            
            model_names.append(name)
            accuracies.append(avg_acc)
            latencies.append(avg_lat)
            
            print(f"   🔹 {name}: Accuracy={avg_acc:.2f}%, Time={avg_lat:.2f}s")
        except Exception as e:
            print(f"   ⚠️ Could not read {file}: {e}")

    # 3. Plotting the Graph (Dual Axis)
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Bar Locations
    x = range(len(model_names))
    width = 0.35

    # Plot Accuracy (Blue Bars)
    ax1.bar([i - width/2 for i in x], accuracies, width, label='Accuracy (%)', color='#4f86f7', alpha=0.7)
    ax1.set_xlabel('AI Models', fontsize=12)
    ax1.set_ylabel('Average Accuracy (%)', color='#4f86f7', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='#4f86f7')
    ax1.set_ylim(0, 100) # Accuracy is 0-100%

    # Create a second y-axis for Latency (Red Line/Dots)
    ax2 = ax1.twinx()
    ax2.plot(x, latencies, color='#e04f5f', marker='o', linewidth=2, label='Latency (s)')
    ax2.set_ylabel('Average Response Time (seconds)', color='#e04f5f', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='#e04f5f')
    ax2.set_ylim(0, max(latencies) + 5) # Add some headroom

    # Labels and Title
    plt.title('RAG Benchmark: Accuracy vs Speed', fontsize=14, pad=20)
    plt.xticks(x, model_names)
    
    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2)

    # Save and Show
    plt.tight_layout()
    output_file = "benchmark_comparison_graph.png"
    plt.savefig(output_file, dpi=300)
    print(f"\n✅ Graph saved as '{output_file}'. Opening preview...")
    plt.show()

if __name__ == "__main__":
    generate_comparison_graph()
    