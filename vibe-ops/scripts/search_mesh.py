import sys
import os
import argparse

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from storage.vector_store import VectorStore

def main():
    parser = argparse.ArgumentParser(description="Search the Vibe-Ops Data Mesh using RAG.")
    parser.add_argument("query", type=str, help="The semantic query.")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return.")
    args = parser.parse_args()

    # Note: Using the default persist_directory './chroma_db'
    # In a real scenario, this should be configurable.
    vector_db = VectorStore()
    
    print(f"\n--- Searching for: '{args.query}' ---\n")
    results = vector_db.query_semantic(args.query, n_results=args.limit)
    
    if not results or not results['ids'][0]:
        print("No results found.")
        return

    for i in range(len(results['ids'][0])):
        node_id = results['ids'][0][i]
        distance = results['distances'][0][i]
        metadata = results['metadatas'][0][i]
        
        print(f"[{i+1}] Node: {node_id} (Distance: {distance:.4f})")
        print(f"    Domain: {metadata.get('domain', 'N/A')}")
        print(f"    Type: {metadata.get('entity_type', 'N/A')}")
        print(f"    Snippet: {metadata.get('content_snippet', 'No snippet available...')}")
        print("-" * 40)

if __name__ == "__main__":
    main()
