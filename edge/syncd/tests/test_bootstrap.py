"""Unit tests for journal-prefix bootstrap (T-05).

These exercise the pure contiguity check, which is the gate deciding whether an
edge may be promoted. End-to-end paging against a live core is covered by the
integration test in test_partition_and_boundary_visibility.py.
"""

from __future__ import annotations

from src.bootstrap import verify_contiguous_prefix


def test_empty_journal_is_a_valid_empty_prefix() -> None:
    # An incident with no events yet is legitimately bootstrapped.
    assert verify_contiguous_prefix(0, None, None) is True


def test_full_contiguous_prefix_accepted() -> None:
    assert verify_contiguous_prefix(5, 1, 5) is True


def test_single_event_prefix_accepted() -> None:
    assert verify_contiguous_prefix(1, 1, 1) is True


def test_gap_in_sequence_rejected() -> None:
    # Rows 1,2,3,5 -> count 4 but max 5: one sequence number is missing.
    assert verify_contiguous_prefix(4, 1, 5) is False


def test_prefix_not_starting_at_one_rejected() -> None:
    # A suffix (3..7) is not a prefix; promoting on it would lose history.
    assert verify_contiguous_prefix(5, 3, 7) is False


def test_row_count_without_bounds_rejected() -> None:
    # Inconsistent aggregate state must never read as contiguous.
    assert verify_contiguous_prefix(3, None, None) is False


def test_zero_count_with_bounds_rejected() -> None:
    assert verify_contiguous_prefix(0, 1, 5) is False
