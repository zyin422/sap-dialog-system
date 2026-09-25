from operator import mod
import librosa, torch, time
from transformers import AutoProcessor
from transformers import AutoModelForCausalLM, AutoTokenizer
from dataclasses import dataclass, asdict
import abc, pathlib, json, typing

from s2t_pipeline import BaseLLM, LLMInstruct

def get_default_device() -> str:
  if torch.cuda.is_available():
    return "cuda"
  if torch.backends.mps.is_available():
    return "mps"
  return "cpu"

transcripts = [
    # --- 5 Existing Pipeline Benchmarks ---
    {
        "id": 1,
        "category": "definition",
        "transcript": "Define conclude.",
        "expected_intent": "definition_request",
        "expected_slots": {
            "word": "conclude"
        }
    },
    {
        "id": 2,
        "category": "media_search",
        "transcript": "Show me an image of business meetings.",
        "expected_intent": "show_image",
        "expected_slots": {
            "query": "business meetings"
        }
    },
    {
        "id": 3,
        "category": "finance",
        "transcript": "What is the Microsoft stock price?",
        "expected_intent": "get_stock_price",
        "expected_slots": {
            "company": "Microsoft"
        }
    },
    {
        "id": 4,
        "category": "weather",
        "transcript": "What is the weather on New Year's Eve?",
        "expected_intent": "check_weather",
        "expected_slots": {
            "date": "New Year's Eve"
        }
    },
    {
        "id": 5,
        "category": "alarm",
        "transcript": "Wake me up at 6:45 every day.",
        "expected_intent": "set_alarm",
        "expected_slots": {
            "time": "6:45",
            "frequency": "every day"
        }
    },
    {
        "id": 6,
        "category": "device_control",
        "transcript": "Turn the TV to CBS.",
        "expected_intent": "device_control",
        "expected_slots": {
            "device": "TV",
            "channel": "CBS"
        }
    },
    {
        "id": 7,
        "category": "information_query",
        "transcript": "What film won the Oscar 1949?",
        "expected_intent": "information_query",
        "expected_slots": {
            "award": "Oscar",
            "category": "film",
            "year": "1949"
        }
    },
    {
        "id": 8,
        "category": "places_search",
        "transcript": "Show me nearby shopping malls.",
        "expected_intent": "find_places",
        "expected_slots": {
            "place_type": "shopping malls",
            "location": "nearby"
        }
    },
    {
        "id": 9,
        "category": "recipe_query",
        "transcript": "Recipe with cilantro, and garlic, and chicken.",
        "expected_intent": "find_recipe",
        "expected_slots": {
            "ingredients": ["cilantro", "garlic", "chicken"]
        }
    },
    {
        "id": 10,
        "category": "media_audiobook",
        "transcript": "Read 'For Whom the Bell Tolls' on Audiobook.",
        "expected_intent": "play_audiobook",
        "expected_slots": {
            "title": "For Whom the Bell Tolls",
            "media_type": "audiobook"
        }
    }
]


candidate_models = [
    # "Qwen/Qwen2.5-7B-Instruct",
    # "Qwen/Qwen2.5-14B-Instruct",
    # "meta-llama/Llama-3.1-8B-Instruct",
    # "NousResearch/Hermes-3-Llama-3.1-8B",
    "meta-llama/Llama-3.2-3B-Instruct",
]

@dataclass
class LLMResult:
    timestamp: str
    llm_outputs: list[dict[str, typing.Any]]

class LLMEvalution:
    def __init__(self, transcripts: list, llm: BaseLLM):
        self.transcripts = transcripts
        self.llm = llm

    def process_transcripts(self) -> LLMResult:
        print(f"Processing {self.llm.model_id}")
        result = []
        for t in transcripts:

            print(f"")
            t_llm = time.perf_counter()

            output = self.llm.inference(t["transcript"])
            llm_duration = time.perf_counter() - t_llm
            result.append(
                {
                    "id": t["id"],
                    "transcript": t["transcript"],           # The input text
                    "expected_intent": t["expected_intent"], # Ground truth
                    "expected_slots": t["expected_slots"],
                    "llm_output": output,
                    "latency_seconds": round(llm_duration, 2)
                }
            )

            print(f"Inference time: {llm_duration:.2f}s")
        return LLMResult(timestamp=t_llm, llm_outputs=result)

    
    def save_results(self, results: LLMResult, output_file: str | pathlib.Path) -> None:
        output_path = pathlib.Path(output_file)
        if output_path.suffix.lower() == ".json":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            data = json.dumps(asdict(results), indent=2)
            output_path.write_text(data)
    


if __name__ == "__main__":
    for m in candidate_models:
        print("Loading LLM model...")
        t0 = time.perf_counter()
        llm = LLMInstruct(model_id=m)
        print(f"Evaluating {m}")
        eval = LLMEvalution(transcripts = transcripts, llm=llm)
        results = eval.process_transcripts()

        safe_model_id = m.replace("/", "_")
        output_path = pathlib.Path("eval_results") / f"{safe_model_id}_results.json"


        eval.save_results(results, output_path)
        print(f"Results saved to {output_path}")


        for r in results.llm_outputs: # loop through transcripts
            print("\n\n\n---------------")  
            print(f"Transcript: {r['transcript']}")
            print(f"LLM Output: {r['llm_output']}")
            
        del llm
        del eval
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()