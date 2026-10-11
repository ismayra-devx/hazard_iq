"""
Amazon DynamoDB Report Persistence Service.
Saves citizen hazard reports to DynamoDB table (HazardIQ_Hotspots) or local fallback.

Key Rules:
- Table partition key: `report_id`.
- Never reports persistence success if a write fails.
- Distinguishes persistence status from hazard verification status.
- When AWS is disabled, falls back to a reliable local/test repository.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DynamoDBReportService:
    def __init__(
        self,
        table_name: Optional[str] = None,
        region_name: Optional[str] = None,
        aws_integration_enabled: Optional[bool] = None,
    ):
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE", "HazardIQ_Hotspots")
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-southeast-2")
        self.aws_enabled = (
            aws_integration_enabled
            if aws_integration_enabled is not None
            else os.getenv("AWS_INTEGRATION_ENABLED", "false").lower() == "true"
        )
        self._table = None
        # Local in-memory repository for local development and offline testing
        self._local_reports: Dict[str, Dict[str, Any]] = {}

    def get_table(self):
        """Lazy load boto3 DynamoDB Table resource."""
        if not self.aws_enabled:
            return None
        if self._table is None:
            try:
                import boto3
                dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
                self._table = dynamodb.Table(self.table_name)
            except Exception as e:
                logger.warning("Could not initialize DynamoDB table %s: %s", self.table_name, str(e))
                self._table = None
        return self._table

    async def save_report(self, report_item: Dict[str, Any]) -> str:
        """
        Persist report to DynamoDB or local test store.

        Returns:
            persistence_status: 'stored', 'local_stored', 'not_configured', or 'failed'
        """
        report_id = report_item.get("report_id")

        if not self.aws_enabled:
            # Local development fallback
            if report_id:
                self._local_reports[report_id] = report_item
            return "not_configured"

        table = self.get_table()
        if table is None:
            logger.error("DynamoDB table resource unavailable for save_report")
            return "failed"

        try:
            # DynamoDB requires decimals or plain types; sanitize None or incompatible values
            cleaned_item = {}
            for k, v in report_item.items():
                if v is not None:
                    cleaned_item[k] = v
                else:
                    cleaned_item[k] = "null"

            table.put_item(Item=cleaned_item)
            return "stored"
        except Exception as e:
            logger.error(
                "DynamoDB put_item failed for report %s in table %s: %s",
                report_id,
                self.table_name,
                str(e),
                exc_info=False
            )
            return "failed"

    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve report from DynamoDB or local store."""
        if not self.aws_enabled:
            return self._local_reports.get(report_id)

        table = self.get_table()
        if table is None:
            return None

        try:
            response = table.get_item(Key={"report_id": report_id})
            return response.get("Item")
        except Exception as e:
            logger.error("Failed to fetch report %s from DynamoDB: %s", report_id, str(e))
            return None

    async def list_reports(self, limit: int = 25) -> List[Dict[str, Any]]:
        """List recent reports."""
        if not self.aws_enabled:
            return list(self._local_reports.values())[:limit]

        table = self.get_table()
        if table is None:
            return []

        try:
            response = table.scan(Limit=limit)
            return response.get("Items", [])
        except Exception as e:
            logger.error("Failed to scan DynamoDB table: %s", str(e))
            return []


# Singleton instance
dynamodb_service = DynamoDBReportService()
