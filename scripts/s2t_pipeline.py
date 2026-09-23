import librosa, torch, time
from transformers import AutoProcessor, VoxtralRealtimeForConditionalGeneration, TextIteratorStreamer
from transformers import AutoModelForCausalLM, AutoTokenizer
from dataclasses import dataclass, asdict
from threading import Thread
import abc, pathlib, json, typing
import numpy as np

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
        t_asr = time.perf_counter()
        transcript = self.asr.transcribe(audio_path)
        asr_duration = time.perf_counter() - t_asr
        print(f"      Transcript: {transcript}")


        print(f"[2/2 Running LLM...")
        t_llm = time.perf_counter()
        inference_result = self.llm.inference(transcript)
        llm_duration = time.perf_counter() - t_llm

        print(f"ASR time: {asr_duration:.2f}s | LLM time: {llm_duration:.2f}s")
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
    def __init__(self, model_id: str = "mistralai/Voxtral-Mini-4B-Realtime-2602", device: str = None, streaming: bool = False, transcription_delay_ms: int = 480):
        self.model_id = model_id
        self.device = device or get_default_device()
        self.streaming = streaming
        self.transcription_delay_ms = transcription_delay_ms
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = VoxtralRealtimeForConditionalGeneration.from_pretrained(model_id, dtype = torch.bfloat16, device_map="auto")
        print(f"Voxtral Model Device:       {self.model.device}")
        print(f"Voxtral Device Map:          {getattr(self.model, 'hf_device_map', 'No device_map')}")
        print(f"Streaming Mode:             {self.streaming}")
        print(f"Transcription Delay:        {self.transcription_delay_ms}ms")
        self._sync_delay_to_processor(self.transcription_delay_ms)

    def _sync_delay_to_processor(self, transcription_delay_ms: int) -> None:
        cfg = self.processor.mistral_common_audio_config
        cfg.transcription_delay_ms = int(transcription_delay_ms)

    def _as_int(self, value) -> int:
        return int(value() if callable(value) else value)

    def _to_model_device(self, batch):
        return batch.to(self.model.device, dtype=self.model.dtype)

    @torch.no_grad()
    def _transcribe_offline(self, audio_array: np.ndarray) -> str:
        inputs = self.processor(audio_array, sampling_rate=16000, return_tensors="pt")
        inputs = inputs.to(self.device, dtype=self.model.dtype)
        for key, val in inputs.items():
            if hasattr(val, "device"):
                print(f"Input tensor '{key}' is on device: {val.device}")

        outputs = self.model.generate(**inputs, max_new_tokens=64)
        decoded_outputs = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
        return decoded_outputs

    @torch.no_grad()
    def _transcribe_streaming(self, audio_array: np.ndarray) -> str:
        n_right_pad = self._as_int(self.processor.num_right_pad_tokens)
        pad = int(n_right_pad * self.processor.raw_audio_length_per_tok)
        xaudio = np.pad(np.asarray(audio_array, dtype=np.float32), (0, pad))

        first_chunk_inputs = self.processor(
            xaudio[: self.processor.num_samples_first_audio_chunk],
            is_streaming=True,
            is_first_audio_chunk=True,
            return_tensors="pt",
        )
        first_chunk_inputs = self._to_model_device(first_chunk_inputs)

        hop_length = self.processor.feature_extractor.hop_length
        win_length = self.processor.feature_extractor.win_length
        mel_frame_idx = self.processor.num_mel_frames_first_audio_chunk
        start_idx = mel_frame_idx * hop_length - win_length // 2

        def input_features_generator():
            nonlocal mel_frame_idx, start_idx
            yield first_chunk_inputs.input_features
            while True:
                end_idx = start_idx + self.processor.num_samples_per_audio_chunk
                if end_idx > xaudio.shape[0]:
                    break
                chunk = xaudio[start_idx:end_idx]
                inputs = self.processor(
                    chunk,
                    is_streaming=True,
                    is_first_audio_chunk=False,
                    return_tensors="pt",
                )
                inputs = self._to_model_device(inputs)
                yield inputs.input_features
                mel_frame_idx += self.processor.audio_length_per_tok
                start_idx = mel_frame_idx * hop_length - win_length // 2

        streamer = TextIteratorStreamer(
            self.processor.tokenizer,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        gen_kw = {
            "input_ids": first_chunk_inputs.input_ids,
            "input_features": input_features_generator(),
            "streamer": streamer,
            "num_delay_tokens": first_chunk_inputs["num_delay_tokens"],
        }
        thread = Thread(target=self.model.generate, kwargs=gen_kw)
        thread.start()
        parts = []
        for text_chunk in streamer:
            parts.append(text_chunk)
        thread.join()
        return "".join(parts)

    @torch.no_grad()
    def transcribe(self, audio_path):
        audio_array, sr = librosa.load(audio_path, sr=16000)
        if self.streaming:
            return self._transcribe_streaming(audio_array)
        else:
            return self._transcribe_offline(audio_array)

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
        print(f"Qwen Model Device:          {self.model.device}")
        print(f"Qwen Device Map:             {getattr(self.model, 'hf_device_map', 'No device_map')}")

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
        print(f"LLM input_ids device: {inputs['input_ids'].device}")

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
    import sys

    streaming_mode = "--streaming" in sys.argv

    # Parse delay parameter (default 480ms)
    transcription_delay_ms = 480
    for arg in sys.argv[1:]:
        if arg.startswith("--delay="):
            transcription_delay_ms = int(arg.split("=")[1])

    print("Loading ASR and LLM models...")
    t0 = time.perf_counter()
    asr = VoxtralRealtimeASR(streaming=streaming_mode, transcription_delay_ms=transcription_delay_ms)
    print(f"Voxtral loaded in {time.perf_counter() - t0:.2f}s")
    llm = QwenLLM()

    print("Creating pipeline:")
    pipeline = SpeechToTextPipeline(asr=asr, llm=llm)

    project_root = pathlib.Path(__file__).parent.parent
    audio_dir = project_root / "audio"
    output_path = project_root / "results.json"

    print(f"Processing audio files from: {audio_dir}")
    results = pipeline.process_directory(str(audio_dir))


    pipeline.save_results(results, output_path)
    print(f"Results saved to {output_path}")

    for r in results:
        print("\n\n\n---------------")
        print(f"File:       {r.audio_file}")
        print(f"Transcript: {r.asr_transcript}")
        print(f"LLM Output: {r.llm_output}")
