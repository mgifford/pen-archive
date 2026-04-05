import json
import os
from pydantic import BaseModel, Field
import instructor
from ollama import Client
from typing import List, Optional
from pathlib import Path
from query_logger import log_query

class DetectedEntities(BaseModel):
    people: List[str] = Field(default_factory=list, description="Names of people found in the text.")
    places: List[str] = Field(default_factory=list, description="Names of places found in the text.")
    organizations: List[str] = Field(default_factory=list, description="Names of organizations or acronyms found in the text.")

class ProcessedDocument(BaseModel):
    markdown_content: str = Field(..., description="The cleaned, corrected Markdown text. Use [[Name]] for people and [Place] for places.")
    date: str = Field(..., description="The extracted publication date. e.g. June 2025")
    volume: Optional[str] = Field(None, description="Volume number if found.")
    issue: Optional[str] = Field(None, description="Issue number if found.")
    detected_entities: DetectedEntities

class OllamaProcessor:
    def __init__(self, model_name: str = "phi3"):
        self.model_name = model_name
        self.client = instructor.from_ollama(Client(), mode=instructor.Mode.JSON)
        
        glossary_path = Path(__file__).parent / "config" / "glossary.json"
        with open(glossary_path, 'r') as f:
            self.glossary_data = json.load(f)

    def get_glossary_for_date(self, date_str: str) -> dict:
        """Determines the correct era glossary based on the date."""
        if "198" in date_str:
            return self.glossary_data.get("1980s", {})
        elif "199" in date_str:
            return self.glossary_data.get("1990s", {})
        else:
            return self.glossary_data.get("default", {})

    def process(self, raw_markdown: str, metadata: dict) -> str:
        date_str = metadata.get('inferred_date', '')
        glossary = self.get_glossary_for_date(date_str)
        
        system_prompt = (
            "You are an expert archivist. Your task is to clean up OCR text from an old newspaper scan. "
            "1. Fix any obvious typos or OCR artifacts.\n"
            "2. Ensure the output is valid Markdown.\n"
            "3. If you spot these local entities, make sure they are spelled correctly and wrap people in [[Name]] and places in [Place].\n"
            f"Known Local Glossary for this era: {json.dumps(glossary)}\n\n"
            "Output the structured data."
        )
        
        # Call the local model using instructor structure
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the text to clean:\n\n{raw_markdown}"}
            ],
            response_model=ProcessedDocument,
        )
        
        # Frugal AI Tracker logging (we approximate response for instructor)
        log_query(
            model=self.model_name,
            system_prompt=system_prompt,
            user_prompt=raw_markdown[:500] + "... [truncated]",
            response=response.model_dump_json(),
            task_name="cleanup_and_extract_metadata"
        )
        
        # Format the final Markdown file string
        yaml_frontmatter = (
            "---\n"
            f"date: {metadata.get('inferred_date', 'Unknown')}\n"
            f"original_url: {metadata.get('original_url', '')}\n"
            f"volume: {response.volume or 'Unknown'}\n"
            f"issue: {response.issue or 'Unknown'}\n"
        )
        
        if response.detected_entities:
            yaml_frontmatter += "detected_entities:\n"
            for entity_type, entities in response.detected_entities.model_dump().items():
                if entities:
                    yaml_frontmatter += f"  {entity_type}:\n"
                    for entity in entities:
                        yaml_frontmatter += f"    - {entity}\n"
                        
        yaml_frontmatter += "---\n\n"
        
        return yaml_frontmatter + response.markdown_content
