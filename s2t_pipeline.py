import librosa
import torch
from transformers import AutoProcessor, VoxtralRealtimeForConditionalGeneration
from transformers import AutoModelForCausalLM, AutoTokenizer
from dataclasses import dataclass, asdict
import abc, pathlib, json, typing

def get_default_device() -> str:
  if torch.cuda.is_available():
    return "cuda"
  if torch.backends.mps.is_available():
    return "mps"
  return "cpu"

@dataclass
class PipelineResult:
    audio_file: str | pathlib.Path
    asr_transcript: str
    llm_output: dict[str, typing.Any]
    ground_truth: typing.Optional[str] = None

class BaseASR(abc.ABC):
    @abc.abstractmethod
    def transcribe(self, audio_path: str | pathlib.Path) -> str:
        pass

class BaseLLM(abc.ABC):
    @abc.abstractmethod
    def inference(self, transcript: str) -> dict[str, typing.Any]:
        pass

class SpeechToTextPipeline:
    def __init__(self, asr: BaseASR, llm: BaseLLM):
        self.asr = asr
        self.llm = llm

    def process_file(self, audio_path: str | pathlib.Path, ground_truth: typing.Optional[str] = None) -> PipelineResult:
        print(f"\n[1/2] Running ASR...")
        transcript = self.asr.transcribe(audio_path)
        print(f"      Transcript: {transcript}")

        print(f"[2/2 Running LLM...")
        inference_result = self.llm.inference(transcript)
        return PipelineResult(audio_file=str(audio_path), asr_transcript=transcript, llm_output=inference_result, ground_truth=ground_truth)
    
    def process_directory(self, dir_path: str) -> list[PipelineResult]:
        path = pathlib.Path(dir_path)
        files = [f for f in path.iterdir() if f.suffix in [".mp3", ".wav"]]
        results = []
        for f in files:
            results.append(self.process_file(f))

        return results
    
    def save_results(self, results:list[PipelineResult], output_file: str | pathlib.Path) -> None:
        output_path = pathlib.Path(output_file)
        if output_path.suffix.lower() == ".json":
            data = json.dumps([asdict(p) for p in results])
            output_path.write_text(data)

class VoxtralRealtimeASR(BaseASR):
    def __init__(self, model_id: str = "mistralai/Voxtral-Mini-4B-Realtime-2602", device: str = None):
        self.model_id = model_id
        self.device = device or get_default_device()
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = VoxtralRealtimeForConditionalGeneration.from_pretrained(model_id, dtype = torch.bfloat16, device_map="auto")

    @torch.no_grad()
    def transcribe(self, audio_path):
        audio_array, sr = librosa.load(audio_path, sr=16000)
        inputs = self.processor(audio_array, sampling_rate=sr, return_tensors="pt")
        inputs = inputs.to(self.device, dtype=self.model.dtype)
        outputs = self.model.generate(**inputs, max_new_tokens=64) # type: ignore[bad-argument-type]
        decoded_outputs = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
        
        return decoded_outputs

class QwenLLM(BaseLLM):
    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-7B-Instruct",
        device: str = None,
    ):
        self.model_id = model_id
        self.device = device or get_default_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, dtype = torch.bfloat16, device_map="auto")

    @torch.no_grad()
    def inference(self, transcript: str):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI task assistant in a spoken dialog system helping users with speech dysarthria perform tasks "
                    "(e.g. setting alarms, checking weather, calendar scheduling).\n"
                    "Analyze the user's spoken transcript, which may contain dysfluent or imperfect speech recognition errors.\n"
                    "Respond ONLY with a valid JSON object containing:\n"
                    "1. 'intent': the identified task or action (string)\n"
                    "2. 'slots': key-value pairs of extracted entities (e.g. time, date, location, item)\n"
                    "3. 'response': a natural, helpful conversational response to the user\n"
                    "Do not include Markdown formatting or any extra text outside the JSON file."
                )
            },
            {
                "role": "user",
                "content": f"Spoken Transcript: {transcript}",
            },
        ]

        text = self.tokenizer.apply_chat_template( #type: ignore
            messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.device) #type: ignore
        outputs = self.model.generate(**inputs, max_new_tokens=256)

        prompt_length = inputs["input_ids"].shape[1]
        new_tokens = outputs[0][prompt_length:]
        decoded_outputs = self.tokenizer.decode(new_tokens, skip_special_tokens=True) #type: ignore

        clean_text = decoded_outputs.strip()
        start = clean_text.find("{")
        end = clean_text.rfind("}")
        if start != -1 and end != -1:
            clean_text = clean_text[start : end + 1]

        try:
            out = json.loads(clean_text)
            return out
        except:
            print("json.loads failed:")
            return {"raw_output": clean_text}


if __name__ == "__main__":
    print("Loading ASR and LLM models...")
    asr = VoxtralRealtimeASR()
    llm = QwenLLM()

    print("Creating pipeline:")
    pipeline = SpeechToTextPipeline(asr=asr, llm=llm)

    current_dir = pathlib.Path(__file__).parent
    audio_dir = current_dir / "audio"
    output_path = current_dir / "results.json"

    print(f"Processing audio files from: {audio_dir}")
    results = pipeline.process_directory(str(audio_dir))


    pipeline.save_results(results, output_path)
    print(f"Results saved to {output_path}")

    for r in results:
        print("\n\n\n---------------")
        print(f"File:       {r.audio_file}")
        print(f"Transcript: {r.asr_transcript}")
        print(f"LLM Output: {r.llm_output}")
