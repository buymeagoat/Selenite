"""Routes for managing ASR/diarizer providers."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.model_registry import (
    ModelWeightCreate,
    ModelWeightResponse,
    ModelWeightUpdate,
    ModelSetCreate,
    ModelSetResponse,
    ModelSetUpdate,
    ModelSetWithWeights,
)
from app.services.model_registry import ModelRegistryService

router = APIRouter(prefix="/models/providers", tags=["model-providers"])
logger = logging.getLogger("app.routes.model_registry")


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )


@router.get("", response_model=list[ModelSetWithWeights])
async def list_model_sets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return registered providers for the admin console or user overrides."""

    try:
        if current_user.is_admin:
            return await ModelRegistryService.list_model_sets(session)
        return await ModelRegistryService.list_visible_model_sets(session)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list model providers")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load model providers",
        )


@router.post("", response_model=ModelSetResponse, status_code=status.HTTP_201_CREATED)
async def create_model_set(
    payload: ModelSetCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Register a new provider and auto-expose it."""

    _require_admin(current_user)

    try:
        model_set = await ModelRegistryService.create_model_set(
            session, payload, current_user.username
        )
    except ValueError as exc:
        logger.warning("Failed to create model set %s: %s", payload.name, exc)
        if str(exc) == "set_name_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Model set name already exists",
            ) from exc
        _raise_path_error(exc)
        raise

    return model_set


@router.patch("/{set_id}", response_model=ModelSetResponse)
async def update_model_set(
    set_id: int,
    payload: ModelSetUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Update metadata or toggle a provider."""

    _require_admin(current_user)

    model_set = await ModelRegistryService.get_set_by_id(session, set_id)
    if not model_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model set not found")

    try:
        updated = await ModelRegistryService.update_model_set(
            session, model_set, payload, current_user.username
        )
    except ValueError as exc:
        if str(exc) == "disable_reason_required":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Disable reason required when turning a set off",
            ) from exc
        if str(exc) == "set_name_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Model set name already exists",
            ) from exc
        _raise_path_error(exc)
        raise

    return updated


@router.delete("/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_set(
    set_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a model set and its entries."""

    _require_admin(current_user)

    model_set = await ModelRegistryService.get_set_by_id(session, set_id)
    if not model_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model set not found")

    await ModelRegistryService.delete_model_set(session, model_set, current_user.username)
    return {"detail": "deleted"}


@router.post(
    "/{set_id}/weights", response_model=ModelWeightResponse, status_code=status.HTTP_201_CREATED
)
async def create_model_weight(
    set_id: int,
    payload: ModelWeightCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create a concrete model weight under a set."""

    _require_admin(current_user)

    model_set = await ModelRegistryService.get_set_by_id(session, set_id)
    if not model_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model set not found")

    try:
        entry = await ModelRegistryService.create_model_weight(
            session, model_set, payload, current_user.username
        )
    except ValueError as exc:
        logger.warning(
            "Failed to create model weight %s under set %s: %s", payload.name, model_set.name, exc
        )
        _raise_weight_error(exc)
    return entry


@router.patch("/weights/{weight_id}", response_model=ModelWeightResponse)
async def update_model_weight(
    weight_id: int,
    payload: ModelWeightUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Update metadata or toggle a model weight."""

    _require_admin(current_user)

    entry = await ModelRegistryService.get_weight_by_id(session, weight_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model weight not found")

    try:
        updated = await ModelRegistryService.update_model_weight(
            session, entry, payload, current_user.username
        )
    except ValueError as exc:
        _raise_weight_error(exc)
    return updated


@router.delete("/weights/{weight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_weight(
    weight_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a model weight."""

    _require_admin(current_user)

    entry = await ModelRegistryService.get_weight_by_id(session, weight_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model weight not found")

    await ModelRegistryService.delete_model_weight(session, entry, current_user.username)
    return {"detail": "deleted"}


def _raise_weight_error(exc: ValueError) -> None:
    message = str(exc)
    if message in {"entry_name_exists", "weight_name_exists"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Weight name already exists"
        ) from exc
    if message == "disable_reason_required":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disable reason required when turning a weight off",
        ) from exc
    if message == "missing_weights":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enable a model weight until its files exist on disk",
        ) from exc
    _raise_path_error(exc)
    raise exc


def _raise_path_error(exc: ValueError) -> None:
    message = str(exc)
    if message in {
        "path_must_be_absolute",
        "path_outside_models",
        "path_outside_set",
        "path_missing",
        "invalid_path",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid model path provided"
        ) from exc
