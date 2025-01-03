import os
import json
from openai import AsyncOpenAI, OpenAI
from dotenv import load_dotenv
from fastapi import HTTPException
from common.logging import setup_logger

logger = setup_logger()


class GPTService:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("API key not found in environment.")
            raise ValueError("Missing OPENAI_API_KEY in environment.")
        self.gpt_client = OpenAI(api_key=api_key)
        self.gpt_async_client = AsyncOpenAI(api_key=api_key)

    def _load_prompts(self, prompt_files=None):
        prompt_dir = os.getenv("PROMPT_ENGINEERING_DIR_PATH")
        prompt_files = prompt_files or {
            "Classify": "ClassifyPr.txt",
            "ES": "onlyES.txt",
            "DB": "onlyMDB.txt",
            "Policy": "policy.txt",
            "Summary": "DetailPr.txt",
            "Report": "reportPr.md",
            "InitReport": "reportPr_init.md",
            "Recommend": "recomm.txt",
            "Graph": "graphPr.txt",
            "ReportCheck": "reportcheck.txt",
            "DailyInsight": "dailyInsight.txt",
            "Dashboard": "DashPr.txt"
        }

        init_prompts = {}
        for name, file_name in prompt_files.items():
            path = os.path.join(prompt_dir, file_name)
            init_prompts[name] = [{"role": "system", "content": self._read_prompt(path)}]
        return init_prompts

    def _read_prompt(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {file_path}")
            raise HTTPException(status_code=500, detail=f"Prompt file not found: {file_path}")

    def _clean_response(self, response):
        choices = getattr(response, "choices", [])
        return choices[0].message.content if choices and hasattr(choices[0].message, 'content') else None

    def _clean_streaming_chunk(self, chunk):
        choices = getattr(chunk, "choices", None)
        return choices[0].delta.content if choices and choices[0].delta.content else None

    async def get_response(self, messages, json_format=True, recomm=False, response_format=None):
        try:
            if not response_format:
                response_format = {"type": "json_object"} if json_format else None
            presence_penalty = 1.5 if recomm else 0
            
            response = await self.gpt_async_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format=response_format,
                presence_penalty=presence_penalty
            )
            return self._clean_response(response)
        except Exception as e:
            logger.error(f"Error fetching GPT response: {e}")
            raise HTTPException(status_code=500, detail="GPT API error")

    async def stream_response(self, messages):
        try:
            stream = self.gpt_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                clean_answer = self._clean_streaming_chunk(chunk)
                if clean_answer:
                    yield clean_answer
        except Exception as e:
            logger.error(f"Error during streaming GPT response: {e}")
            raise HTTPException(status_code=500, detail="GPT streaming API error")

    def _load_meta_schema(self, schema_path: str) -> dict:
        try:
            with open(schema_path, "r", encoding="utf-8") as schema_file:
                return json.load(schema_file)
        except FileNotFoundError:
            raise RuntimeError(f"Schema file not found: {schema_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in schema file: {e}")
