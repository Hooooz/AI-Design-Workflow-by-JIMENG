import re
import json
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


class LLMResponseProcessor:
    """
    Centralized processor for handling, cleaning, and normalizing LLM JSON responses.
    """

    @staticmethod
    def clean_json_string(raw_text: str) -> str:
        """
        Clean raw LLM output to extract valid JSON string.
        """
        if not raw_text:
            return ""

        json_str = raw_text.strip()

        # 1. Extract from Markdown code blocks
        match = re.search(
            r"```(?:json)?\s*(.*?)```", json_str, re.DOTALL | re.IGNORECASE
        )
        if match:
            json_str = match.group(1).strip()
        else:
            # 2. Extract from outermost braces if no code block
            start = json_str.find("{")
            end = json_str.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = json_str[start : end + 1]

        # 3. Remove control characters (preserve newlines/tabs)
        json_str = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", json_str)

        return json_str

    @staticmethod
    def safe_parse_json(json_str: str) -> Dict[str, Any]:
        """
        Parse JSON string with error handling and encoding fixes.
        """
        try:
            # Fix potential encoding issues
            json_bytes = json_str.encode("utf-8", errors="replace")
            clean_str = json_bytes.decode("utf-8", errors="replace")
            return json.loads(clean_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            logger.error(f"Problematic JSON prefix: {json_str[:500]}...")
            raise e

    @staticmethod
    def normalize_keys(
        data: Dict[str, Any], key_mapping: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Normalize dictionary keys based on a mapping of {canonical_key: [aliases]}.
        """
        normalized = data.copy()

        for canonical, aliases in key_mapping.items():
            # If canonical key already exists and has value, skip
            if normalized.get(canonical):
                continue

            # Search for aliases
            for alias in aliases:
                if val := normalized.get(alias):
                    normalized[canonical] = val
                    break

            # Ensure key exists (default to empty if not found)
            if canonical not in normalized:
                normalized[canonical] = "" if canonical != "prompts" else []

        return normalized

    @staticmethod
    def extract_list(
        data: Dict[str, Any], list_key: str = "prompts"
    ) -> List[Dict[str, Any]]:
        """
        robustly extract a list from a dictionary, handling nested structures.
        """
        # 1. Direct access
        val = data.get(list_key)
        if isinstance(val, list):
            return val

        # 2. Check if the value is a dict containing the list (e.g. {"prompts": {"list": [...]}})
        if isinstance(val, dict):
            for sub_key in ["list", "items", "data", "values", "details"]:
                if isinstance(val.get(sub_key), list):
                    return val[sub_key]

        # 3. Fallback: Check other common list keys at root level if main key failed
        common_list_keys = ["prompts", "visuals", "images", "schemes", "items", "list"]
        for key in common_list_keys:
            if isinstance(data.get(key), list):
                return data[key]

        return []

    @classmethod
    def process_market_analysis(cls, raw_response: str) -> Dict[str, Any]:
        """Process output from Market Analyst agent."""
        data = cls.safe_parse_json(cls.clean_json_string(raw_response))

        mapping = {
            "summary": ["摘要", "核心摘要", "summary_text", "conclusion"],
            "content": ["内容", "报告", "report", "analysis", "market_analysis"],
            "visuals": ["prompts", "images", "pictures", "visual_concepts"],
        }

        normalized = cls.normalize_keys(data, mapping)
        normalized["visuals"] = cls.extract_list(normalized, "visuals")
        return normalized

    @classmethod
    def process_visual_research(cls, raw_response: str) -> Dict[str, Any]:
        """Process output from Visual Researcher agent."""
        data = cls.safe_parse_json(cls.clean_json_string(raw_response))

        mapping = {
            "summary": ["摘要", "核心摘要", "summary_text"],
            "content": ["内容", "报告", "report", "research", "visual_research"],
            "visuals": ["prompts", "images", "pictures", "style_concepts"],
        }

        normalized = cls.normalize_keys(data, mapping)
        normalized["visuals"] = cls.extract_list(normalized, "visuals")
        return normalized

    @classmethod
    def process_design_generation(cls, raw_response: str) -> Dict[str, Any]:
        """Process output from Product Designer agent."""
        data = cls.safe_parse_json(cls.clean_json_string(raw_response))

        mapping = {
            "summary": ["摘要", "核心摘要", "设计思路", "design_concept"],
            "prompts": ["schemes", "designs", "proposals", "方案", "设计方案"],
        }

        normalized = cls.normalize_keys(data, mapping)
        normalized["prompts"] = cls.extract_list(normalized, "prompts")

        # Ensure prompts have image_path key
        for item in normalized["prompts"]:
            if isinstance(item, dict) and "image_path" not in item:
                item["image_path"] = ""

        return normalized
