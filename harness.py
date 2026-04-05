import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path
from query_logger import log_query # Frugal AI Tracker
import ollama

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, pdf_path: str) -> str:
        """Extracts text from the given PDF. Returns raw markdown/text."""
        pass

class MockMarkerExtractor(BaseExtractor):
    def extract(self, pdf_path: str) -> str:
        # Represents the heavy deep-learning based Marker pipeline.
        return "# Extracted with Marker\n\nThis is a high-quality column-aware extraction."

class MockTesseractExtractor(BaseExtractor):
    def extract(self, pdf_path: str) -> str:
        # Represents standard OCR followed by custom despaghettification.
        return "EXTRACTED W TESSERACT \n This is standard OCR. Columns might mingle."

class Judge:
    def __init__(self, model_name: str = "phi3"):
        self.model_name = model_name

    def score_extraction(self, text_sample: str) -> int:
        """
        Runs a local LLM to score the coherence of the text from 1 (Gibberish) to 10 (Perfect).
        """
        system_prompt = (
            "You are an expert archivist digitizing old newspapers. "
            "Rate the following text snippet for 'Coherence' and 'Lack of Gibberish' on a scale of 1 to 10. "
            "Only output the single integer score."
        )
        
        # Take a 500 word sample
        words = text_sample.split()
        sample = " ".join(words[:500])
        
        # In a real scenario, use try/except block to handle model availability
        response = ollama.chat(model=self.model_name, messages=[
            {
                'role': 'system',
                'content': system_prompt,
            },
            {
                'role': 'user',
                'content': sample
            }
        ])
        
        reply = response['message']['content'].strip()
        
        # Log to Frugal AI Tracker
        log_query(
            model=self.model_name, 
            system_prompt=system_prompt, 
            user_prompt=sample, 
            response=reply,
            task_name="judge_ocr_quality"
        )
        
        # Parse score
        try:
            # simple parsing just to find a number
            import re
            match = re.search(r'\d+', reply)
            if match:
                score = int(match.group())
                return min(max(score, 1), 10)
            return 5 # fallback
        except Exception:
            return 5

class DigitalArchivistHarness:
    def __init__(self, extractors: Dict[str, BaseExtractor], judge: Judge, processor: Any):
        self.extractors = extractors
        self.judge = judge
        self.processor = processor

    def run_pipeline(self, pdf_path: str, metadata: dict):
        print(f"--- Running pipeline for {pdf_path} ---")
        
        results = {}
        scores = {}
        
        # Phase 2: OCR Competition
        for name, extractor in self.extractors.items():
            print(f"Extracting with {name}...")
            text = extractor.extract(pdf_path)
            results[name] = text
            score = self.judge.score_extraction(text)
            scores[name] = score
            print(f"  {name} score: {score}")
            
        # Determine Winner
        winner_name = max(scores, key=scores.get)
        print(f"🏆 Winner is: {winner_name}")
        winning_text = results[winner_name]
        
        # Phase 3: Cleanup & Enrichment
        print("Cleaning up winning text and enriching metadata...")
        final_doc = self.processor.process(winning_text, metadata)
        
        return final_doc
