import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.graph.workflow import build_workflow

def generate_langgraph_png():
    print("Building LangGraph workflow...")
    workflow = build_workflow()
    
    output_path = os.path.join(root_dir, "docs", "langgraph_workflow.png")
    
    try:
        # LangGraph built-in method to generate PNG via Mermaid representation
        print("Rendering PNG using LangGraph's default get_graph().draw_mermaid_png()...")
        graph = workflow.get_graph()
        png_bytes = graph.draw_mermaid_png()
        
        with open(output_path, "wb") as f:
            f.write(png_bytes)
            
        print(f"[SUCCESS] LangGraph flow diagram successfully saved as PNG to: {output_path}")
    except Exception as e:
        print(f"[ERROR] draw_mermaid_png error: {e}")
        # Fallback to local ascii/mermaid dump if mermaid.ink is blocked
        mermaid_syntax = workflow.get_graph().draw_mermaid()
        print("Mermaid Syntax:")
        print(mermaid_syntax)

if __name__ == "__main__":
    generate_langgraph_png()
