"""
Image Analysis Service using Amazon Bedrock with Amazon Nova Lite.

CRITICAL SAFETY & GOVERNANCE RULES:
- AI image output is strictly an advisory candidate assessment, NOT ground truth or physical measurement.
- The model must never invent exact water depths, stream velocity, or shade percentages.
- Never log raw Base64 image payloads or sensitive report attributes.
- If Bedrock is disabled or credentials are missing, returns clean fallback without failing the report.
"""

import json
import logging
import re
from typing import Optional, Tuple
from datetime import datetime, timezone

from app.config import settings
from app.schemas import ImageAnalysisResult, ReportStatus

logger = logging.getLogger(__name__)


class ImageAnalysisService:
    def __init__(
        self,
        enabled: Optional[bool] = None,
        region: Optional[str] = None,
        model_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.enabled = settings.ENABLE_BEDROCK if enabled is None else enabled
        self.region = settings.AWS_REGION if region is None else region
        self.model_id = settings.BEDROCK_MODEL_ID if model_id is None else model_id
        self.timeout = settings.BEDROCK_TIMEOUT_SECONDS if timeout is None else timeout
        self._bedrock_client = None

    def _get_client(self):
        """Lazily initialize boto3 bedrock-runtime client."""
        if self._bedrock_client is None:
            import boto3
            from botocore.config import Config

            config = Config(
                region_name=self.region,
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                retries={"max_attempts": 3, "mode": "standard"}
            )
            kwargs = {"region_name": self.region, "config": config}
            if getattr(settings, "AWS_ENDPOINT_URL", None):
                kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
            self._bedrock_client = boto3.client("bedrock-runtime", **kwargs)
        return self._bedrock_client

    async def analyze_hazard_image(
        self,
        image_base64: str,
        image_format: str = "jpeg",
    ) -> Tuple[Optional[ImageAnalysisResult], ReportStatus, Optional[str]]:
        """
        Analyze a citizen-submitted photograph for climate hazards.

        Returns:
            Tuple of (ImageAnalysisResult, ReportStatus, limitation_string)
        """
        # 1. Fallback adapter if Bedrock integration is disabled in environment
        if not self.enabled:
            limitation = "Amazon Bedrock integration is unconfigured/disabled; photo stored for manual review."
            logger.info("Bedrock disabled in configuration. Skipping vision inference.")
            return None, ReportStatus.PENDING_REVIEW, limitation

        # 2. Invoke Amazon Bedrock with Amazon Nova Lite
        try:
            client = self._get_client()

            # Clean base64 string
            cleaned_b64 = image_base64.strip()
            if "," in cleaned_b64:
                cleaned_b64 = cleaned_b64.split(",", 1)[1]

            import base64
            image_bytes = base64.b64decode(cleaned_b64)

            # Detect MIME format
            fmt = "jpeg"
            if image_bytes.startswith(b"\x89PNG"):
                fmt = "png"
            elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
                fmt = "webp"

            prompt = (
                "You are an objective urban climate hazard visual evaluator for HazardIQ. "
                "Analyze this commuter-submitted photo for road hazards. "
                "Respond ONLY with a valid JSON object matching this schema:\n"
                "{\n"
                '  "hazard_detected": true/false,\n'
                '  "detected_category": "WATERLOGGING" | "EXTREME_HEAT" | "DAMAGED_WATER_POINT" | "FALLEN_TREE_OBSTRUCTION" | "NONE",\n'
                '  "confidence_score": 0.0 to 1.0,\n'
                '  "visual_indicators": ["list", "of", "observable", "cues"],\n'
                '  "reasoning": "brief factual visual justification"\n'
                "}\n"
                "Do NOT invent numerical water depth, stream speed, or shade percentages."
            )

            # Use Bedrock Converse API format supported by Nova models
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": fmt,
                                "source": {"bytes": image_bytes}
                            }
                        },
                        {"text": prompt}
                    ]
                }
            ]

            response = client.converse(
                modelId=self.model_id,
                messages=conversation,
                inferenceConfig={"maxTokens": 350, "temperature": 0.1}
            )

            # Extract output text
            output_msg = response.get("output", {}).get("message", {}).get("content", [])
            text_blocks = [item.get("text", "") for item in output_msg if "text" in item]
            full_text = " ".join(text_blocks).strip()

            # Extract JSON block
            json_match = re.search(r"\{.*\}", full_text, re.DOTALL)
            if not json_match:
                logger.warning("Bedrock returned non-JSON response: %s", full_text[:120])
                limitation = "AI model returned unstructured response; marked for human review."
                return None, ReportStatus.PENDING_REVIEW, limitation

            parsed = json.loads(json_match.group(0))

            hazard_detected = bool(parsed.get("hazard_detected", False))
            category = parsed.get("detected_category")
            confidence = float(parsed.get("confidence_score", 0.5))
            indicators = parsed.get("visual_indicators", [])
            reasoning = parsed.get("reasoning", "Model visual assessment completed.")

            result = ImageAnalysisResult(
                model_id=self.model_id,
                analyzed_at=datetime.now(timezone.utc),
                hazard_detected=hazard_detected,
                detected_category=category,
                confidence_score=max(0.0, min(1.0, confidence)),
                visual_indicators=indicators if isinstance(indicators, list) else [str(indicators)],
                reasoning=reasoning,
                is_ai_estimate=True
            )

            new_status = ReportStatus.AI_FLAGGED if hazard_detected else ReportStatus.PENDING_REVIEW
            return result, new_status, None

        except Exception as e:
            logger.error("Bedrock vision inference failed: %s", str(e))
            limitation = f"AWS Bedrock image evaluation failed ({type(e).__name__}); report preserved as PENDING_REVIEW."
            return None, ReportStatus.PENDING_REVIEW, limitation


# Singleton instance
image_analysis_service = ImageAnalysisService()
