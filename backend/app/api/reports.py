"""
Citizen Hazard Reports API Router.
Handles report submission, optional photo analysis, risk evaluation, and querying.
"""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas import (
    HazardReportCreate,
    HazardReportResponse,
    ReportContractRequest,
    ReportContractResponse,
)
from app.services.report_service import report_service
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Citizen Hazard Reporting"])


@router.post(
    "/report",
    response_model=ReportContractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit citizen hazard photo report (HazardIQ API Contract)",
    description=(
        "Submitted by the frontend when a user uploads a photo of a hazard. "
        "The backend uses Amazon Nova Lite to evaluate the image, runs the Cedar policy, and returns the verdict."
    ),
)
async def create_hazard_report(payload: ReportContractRequest) -> ReportContractResponse:
    try:
        response = await report_service.process_contract_report(payload)
        return response
    except ValueError as ve:
        logger.warning("Validation error processing hazard report: %s", str(ve))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error("Internal failure processing hazard report: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the hazard report."
        )


@router.get(
    "/reports",
    response_model=List[Dict[str, Any]],
    summary="List recent hazard reports",
    description="Retrieves a list of recent citizen hazard reports from the active storage backend.",
)
async def list_hazard_reports(
    limit: int = Query(25, ge=1, le=100, description="Maximum number of reports to retrieve")
) -> List[Dict[str, Any]]:
    return await storage_service.list_reports(limit=limit)


@router.get(
    "/reports/{report_id}",
    response_model=Dict[str, Any],
    summary="Get single hazard report by ID",
)
async def get_hazard_report(report_id: str) -> Dict[str, Any]:
    report = await storage_service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' was not found."
        )
    return report
