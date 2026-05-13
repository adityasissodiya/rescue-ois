"""Unit tests for command-epoch fencing in accept.py.

Covers the validate_request_epoch helper for the three primary cases:
  (a) accept at current epoch
  (b) reject stale epoch
  (c) reject future epoch

Also covers the missing-header case and the un-initialised epoch-cache case.
These tests do not require a database; they exercise the pure validation
function. End-to-end behaviour is covered by the Phase 4.4 experiment.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.accept import validate_request_epoch


def test_accept_when_request_epoch_matches_current() -> None:
    # Equal -> accept (no exception raised).
    validate_request_epoch(client_epoch=5, current_epoch=5)


def test_reject_stale_epoch_with_409() -> None:
    with pytest.raises(HTTPException) as ei:
        validate_request_epoch(client_epoch=3, current_epoch=5)
    assert ei.value.status_code == 409
    assert ei.value.detail["reason"] == "stale_epoch"
    assert ei.value.detail["current_epoch"] == 5
    assert ei.value.detail["request_epoch"] == 3


def test_reject_future_epoch_with_409() -> None:
    with pytest.raises(HTTPException) as ei:
        validate_request_epoch(client_epoch=7, current_epoch=5)
    assert ei.value.status_code == 409
    assert ei.value.detail["reason"] == "future_epoch"
    assert ei.value.detail["current_epoch"] == 5
    assert ei.value.detail["request_epoch"] == 7


def test_reject_missing_header_with_409() -> None:
    with pytest.raises(HTTPException) as ei:
        validate_request_epoch(client_epoch=None, current_epoch=5)
    assert ei.value.status_code == 409
    assert ei.value.detail["reason"] == "missing_epoch"
    assert ei.value.detail["current_epoch"] == 5


def test_503_when_command_cache_not_initialised() -> None:
    # Pre-startup state: cache is None. Should refuse to make any decision.
    with pytest.raises(HTTPException) as ei:
        validate_request_epoch(client_epoch=5, current_epoch=None)
    assert ei.value.status_code == 503


def test_zero_epoch_is_a_valid_value() -> None:
    # The current_epoch view returns 0 only if the table is empty, which
    # should not happen post-migration (the seed row makes current_epoch >= 1).
    # But the validator must still treat 0 as a legal comparable integer,
    # not falsy-coerced to None.
    with pytest.raises(HTTPException) as ei:
        validate_request_epoch(client_epoch=0, current_epoch=1)
    assert ei.value.status_code == 409
    assert ei.value.detail["reason"] == "stale_epoch"
