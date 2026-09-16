import json
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
import os

import sys

def load_dataset(dataset_name="smoke"):
    filepath = os.path.join(os.path.dirname(__file__), "datasets", f"{dataset_name}.json")
    if not os.path.exists(filepath):
        print(f"Dataset {dataset_name} not found.")
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def evaluate_responses(dataset_name="smoke"):
    print(f"[STARTED] Starting LLM-as-a-Judge Evaluation on '{dataset_name}' dataset...")
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model_name=settings.groq_model,
        temperature=0.0
    )
    
    test_cases = load_dataset(dataset_name)
    if not test_cases:
        return
    
    results = []
    
    eval_prompt = """
    You are an expert IT Support Quality Evaluator. 
    Evaluate the following 'actual_response' based on the user's 'query'.
    Provide a score from 1 to 5 for 'faithfulness' (Is it grounded/safe?) and 'relevance' (Does it answer the query?).
    Output ONLY valid JSON with keys: faithfulness, relevance, reason.
    """
    
    for case in test_cases:
        print(f"Evaluating: {case['id']} - {case['query']}")
        try:
            msg = f"User Query: {case['query']}\nBot Response: {case['actual_response']}"
            res = llm.invoke([
                SystemMessage(content=eval_prompt),
                HumanMessage(content=msg)
            ])
            
            # extract JSON
            content = res.content.strip()
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            score_data = json.loads(content)
            
            case["scores"] = score_data
            case["status"] = "Pass" if score_data.get("faithfulness", 0) >= 4 else "Fail"
            results.append(case)
        except Exception as e:
            print(f"Error evaluating {case['id']}: {e}")
            case["scores"] = {"faithfulness": 0, "relevance": 0, "reason": str(e)}
            case["status"] = "Error"
            results.append(case)
            
        time.sleep(1) # prevent rate limit
        
    # Save to JSON
    os.makedirs("evals", exist_ok=True)
    with open("evals/eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n[DONE] Evaluation Complete! Results saved to evals/eval_results.json")
    
if __name__ == "__main__":
    dataset = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    evaluate_responses(dataset)
