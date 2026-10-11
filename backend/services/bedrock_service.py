"""
Amazon Bedrock Vision Analysis Service.
Uses Claude 3 Haiku (Messages API) on AWS Bedrock to extract visual hazard indicators.

Follows strict safety principles:
- Never invents measurements when visual evidence is insufficient.
- Treats model output as an unverified candidate estimate, never ground truth.
- Fails safely without crashing or leaking credentials when Bedrock is unavailable.
"""

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

try:
    from schemas.report import (
        HeatwaveBedrockAnalysis,
        MonsoonBedrockAnalysis,
    )
except ImportError:
    from backend.schemas.report import (
        HeatwaveBedrockAnalysis,
        MonsoonBedrockAnalysis,
    )

logger = logging.getLogger(__name__)


class BedrockVisionService:
    def __init__(
        self,
        region_name: Optional[str] = None,
        model_id: Optional[str] = None,
        aws_integration_enabled: Optional[bool] = None,
    ):
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-southeast-2")
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
        )
        self.aws_enabled = (
            aws_integration_enabled
            if aws_integration_enabled is not None
            else os.getenv("AWS_INTEGRATION_ENABLED", "false").lower() == "true"
        )
        self._client = None

    def get_client(self):
        """Lazy load boto3 client only when AWS integration is enabled."""
        if not self.aws_enabled:
            return None
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("bedrock-runtime", region_name=self.region_name)
            except Exception as e:
                logger.warning("Could not initialize Bedrock client: %s", str(e))
                self._client = None
        return self._client

    def _determine_media_type(self, raw_bytes: bytes) -> str:
        """Inspect magic bytes to determine image media type for Claude Messages API."""
        if raw_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:16]:
            return "image/webp"
        return "image/jpeg"

    async def analyze_hazard_image(
        self,
        image_bytes: bytes,
        image_base64: str,
        hazard_mode: str,
    ) -> Tuple[Optional[int], Optional[int], str, float, list]:
        """
        Analyze uploaded photograph with Amazon Bedrock Claude 3 Haiku.

        Returns:
            Tuple of:
            - water_depth_inches (Optional[int])
            - shade_coverage_percent (Optional[int])
            - analysis_status (str)
            - confidence (float)
            - limitations (List[str])
        """
        mode = hazard_mode.lower().strip()

        # If AWS integration is disabled, fail safely and gracefully
        if not self.aws_enabled:
            limitations = [
                "AWS Bedrock integration is disabled in local environment.",
                "Visual hazard estimation unavailable; manual review required."
            ]
            return None, None, "analysis_unavailable", 0.0, limitations

        client = self.get_client()
        if client is None:
            limitations = [
                "Bedrock runtime client unavailable or AWS credentials not configured.",
                "Hazard measurement cannot be estimated."
            ]
            return None, None, "analysis_unavailable", 0.0, limitations

        media_type = self._determine_media_type(image_bytes)

        # Build prompt instructions enforcing safety disclaimers
        if mode == "monsoon":
            system_instruction = (
                "You are an advisory climate risk assistant for urban road hazards. "
                "Analyze this road image for monsoon flooding or waterlogging. "
                "IMPORTANT SAFETY RULES:\n"
                "- Estimate only what is visually supported by the photograph.\n"
                "- A single image cannot reliably establish exact water depth without an explicit measurement reference.\n"
                "- Return null for water_depth_inches if depth cannot be estimated responsibly.\n"
                "- Do not invent measurements.\n"
                "- Perspective, lighting, occlusion, and camera angle affect results.\n"
                "- Treat confidence as a model indicator (0.0 to 1.0), not a calibrated ground probability.\n"
                "Return ONLY a valid JSON object with the following keys:\n"
                "{\n"
                '  "water_depth_inches": <integer or null>,\n'
                '  "visual_hazard_indicators": [<string>],\n'
                '  "confidence": <float 0.0 to 1.0>,\n'
                '  "analysis_status": "completed" or "uncertain",\n'
                '  "limitations": [<string>]\n'
                "}"
            )
        else:
            system_instruction = (
                "You are an advisory climate risk assistant for urban road hazards. "
                "Analyze this street image for heatwave solar exposure and shade. "
                "IMPORTANT SAFETY RULES:\n"
                "- Estimate only tree canopy, building shadow, or structure shade coverage percentage (0 to 100).\n"
                "- A photograph cannot establish actual ambient temperature or a person's medical condition.\n"
                "- Return null for shade_coverage_percent if shade cannot be estimated responsibly.\n"
                "- Do not invent measurements.\n"
                "- Treat confidence as a model indicator (0.0 to 1.0), not a calibrated ground probability.\n"
                "Return ONLY a valid JSON object with the following keys:\n"
                "{\n"
                '  "shade_coverage_percent": <integer 0-100 or null>,\n'
                '  "heat_vulnerability_indicators": [<string>],\n'
                '  "confidence": <float 0.0 to 1.0>,\n'
                '  "analysis_status": "completed" or "uncertain",\n'
                '  "limitations": [<string>]\n'
                "}"
            )

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 800,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": system_instruction,
                        },
                    ],
                }
            ],
        }

        try:
            response = client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload),
            )
            response_body = json.loads(response["body"].read().decode("utf-8"))
            content_blocks = response_body.get("content", [])
            output_text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

            # Extract JSON block
            parsed = self._extract_json(output_text)
            if not parsed:
                return (
                    None,
                    None,
                    "uncertain",
                    0.0,
                    ["Model response could not be parsed into valid JSON structured format."]
                )

            if mode == "monsoon":
                schema = MonsoonBedrockAnalysis(**parsed)
                return (
                    schema.water_depth_inches,
                    None,
                    schema.analysis_status,
                    schema.confidence,
                    schema.limitations or ["Image-based estimate; unverified by physical measurement."]
                )
            else:
                schema = HeatwaveBedrockAnalysis(**parsed)
                return (
                    None,
                    schema.shade_coverage_percent,
                    schema.analysis_status,
                    schema.confidence,
                    schema.limitations or ["Image-based estimate; does not measure heat index or WBGT."]
                )

        except Exception as e:
            logger.error("Bedrock invocation failed: %s", str(e), exc_info=False)
            return (
                None,
                None,
                "analysis_unavailable",
                0.0,
                [f"Bedrock service error: {type(e).__name__}. Analysis unavailable."]
            )

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse first valid JSON object from model response text."""
        try:
            return json.loads(text.strip())
        except Exception:
            pass

        # Try regex search between braces
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return None


# Singleton instance
bedrock_service = BedrockVisionService()
