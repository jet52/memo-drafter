"""Tests for record citation extraction from appellate briefs."""

import re
from unittest.mock import patch

import pytest

from src.extractor.record_citations import (
    detect_case_number,
    extract_record_numbers,
    format_items_file,
)


# ---------------------------------------------------------------------------
# extract_record_numbers — parenthesized citations
# ---------------------------------------------------------------------------

class TestParenthesizedCitations:
    """Phase 1: citations inside parentheses."""

    def test_simple_r(self):
        assert extract_record_numbers("(R45)") == {45}

    def test_with_page(self):
        assert extract_record_numbers("(R45:12)") == {45}

    def test_with_page_and_paragraph(self):
        assert extract_record_numbers("(R45:12:¶3)") == {45}

    def test_lowercase(self):
        assert extract_record_numbers("(r45)") == {45}

    def test_range_full_prefix(self):
        assert extract_record_numbers("(R45-R52)") == set(range(45, 53))

    def test_range_short_form(self):
        assert extract_record_numbers("(R45-52)") == set(range(45, 53))

    def test_range_end_less_than_start(self):
        # Treated as two separate items, not a range
        assert extract_record_numbers("(R52-R45)") == {52, 45}

    def test_comma_separated_list(self):
        assert extract_record_numbers("(R12, R14, R16)") == {12, 14, 16}

    def test_comma_list_no_repeated_prefix(self):
        # Numbers after commas still captured
        assert extract_record_numbers("(R12, 14, 16)") == {12, 14, 16}

    def test_rec_prefix(self):
        assert extract_record_numbers("(Rec 123)") == {123}

    def test_rec_dot_prefix(self):
        assert extract_record_numbers("(Rec. 123)") == {123}

    def test_idx_prefix(self):
        assert extract_record_numbers("(Idx 45)") == {45}

    def test_idx_dot_prefix(self):
        assert extract_record_numbers("(Idx. 45)") == {45}


# ---------------------------------------------------------------------------
# extract_record_numbers — bare references
# ---------------------------------------------------------------------------

class TestBareCitations:
    """Phase 2: citations without parentheses."""

    def test_simple_bare_r(self):
        assert extract_record_numbers("See R45 for details") == {45}

    def test_bare_r_with_colon(self):
        assert extract_record_numbers("R45:12") == {45}

    def test_bare_r_dot(self):
        assert extract_record_numbers("R. 123") == {123}

    def test_bare_r_dot_no_space(self):
        assert extract_record_numbers("R.123") == {123}

    def test_bare_r_colon_space(self):
        assert extract_record_numbers("R: 123") == {123}

    def test_bare_rec(self):
        assert extract_record_numbers("Rec 123 shows") == {123}

    def test_bare_rec_dot(self):
        assert extract_record_numbers("Rec. 123 shows") == {123}

    def test_bare_idx(self):
        assert extract_record_numbers("Idx 45") == {45}

    def test_bare_idx_dot(self):
        assert extract_record_numbers("Idx. 45") == {45}

    def test_bare_range(self):
        assert extract_record_numbers("R45-R52 contain") == set(range(45, 53))

    def test_bare_range_short(self):
        assert extract_record_numbers("R45-52 contain") == set(range(45, 53))


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------

class TestCaseInsensitivity:
    def test_uppercase_REC(self):
        assert extract_record_numbers("(REC 10)") == {10}

    def test_mixed_case_idx(self):
        assert extract_record_numbers("IDX 10") == {10}

    def test_lowercase_r_bare(self):
        assert extract_record_numbers("r45") == {45}


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_same_number_multiple_times(self):
        text = "(R45) and again R45 and (R45:12)"
        assert extract_record_numbers(text) == {45}

    def test_multiple_unique(self):
        text = "(R1) (R2) (R3) R4 R5"
        assert extract_record_numbers(text) == {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# False positive avoidance
# ---------------------------------------------------------------------------

class TestFalsePositives:
    def test_nd_rules_not_matched(self):
        # The R in N.D.R.Civ.P. should NOT be treated as a record citation
        text = "N.D.R.Civ.P. 12(b)"
        nums = extract_record_numbers(text)
        # Should not extract 12 from the rule reference
        assert 12 not in nums

    def test_nd_appellate_rules_not_matched(self):
        text = "N.D.R.App.P. 35.1"
        nums = extract_record_numbers(text)
        assert 35 not in nums

    def test_nd_evidence_rules_not_matched(self):
        text = "N.D.R.Ev. 401"
        nums = extract_record_numbers(text)
        assert 401 not in nums

    def test_word_record_not_matched(self):
        # The word "Record" by itself should not trigger
        text = "The Record shows that"
        assert extract_record_numbers(text) == set()

    def test_empty_input(self):
        assert extract_record_numbers("") == set()

    def test_no_citations(self):
        text = "This brief contains no record citations at all."
        assert extract_record_numbers(text) == set()


# ---------------------------------------------------------------------------
# Range expansion edge cases
# ---------------------------------------------------------------------------

class TestRangeExpansion:
    def test_large_range_capped(self):
        # Range > 1000 should be treated as two separate items
        text = "(R1-R5000)"
        nums = extract_record_numbers(text)
        assert nums == {1, 5000}

    def test_single_item_range(self):
        text = "(R10-R10)"
        assert extract_record_numbers(text) == {10}


# ---------------------------------------------------------------------------
# detect_case_number
# ---------------------------------------------------------------------------

class TestDetectCaseNumber:
    def test_case_no_format(self):
        assert detect_case_number("Case No. 20260123") == "20260123"

    def test_case_number_format(self):
        assert detect_case_number("Case Number: 20260123") == "20260123"

    def test_no_dot_format(self):
        assert detect_case_number("No. 20260123") == "20260123"

    def test_dashed_format(self):
        assert detect_case_number("Case No. 54-2020-CV-00012") == "54-2020-CV-00012"

    def test_fallback_to_eight_digit(self):
        text = "Supreme Court 20260123 State v. Smith"
        assert detect_case_number(text) == "20260123"

    def test_no_case_number(self):
        assert detect_case_number("No case number here") == ""


# ---------------------------------------------------------------------------
# format_items_file
# ---------------------------------------------------------------------------

class TestFormatItemsFile:
    def test_basic_output(self):
        result = format_items_file({3, 1, 2}, ["brief.pdf"], "20260123")
        lines = result.strip().split("\n")
        assert lines[0] == "# Record citations extracted from briefs"
        assert "Case: 20260123" in lines[1]
        assert "brief.pdf" in lines[2]
        assert "Total unique items: 3" in lines[4]
        # Items are sorted
        assert lines[5] == "R1"
        assert lines[6] == "R2"
        assert lines[7] == "R3"

    def test_no_case_number(self):
        result = format_items_file({1}, ["brief.pdf"])
        assert "Case:" not in result

    def test_multiple_sources(self):
        result = format_items_file({1}, ["a.pdf", "b.pdf"])
        assert "a.pdf, b.pdf" in result

    def test_empty_set(self):
        result = format_items_file(set(), ["brief.pdf"])
        assert "Total unique items: 0" in result

    @patch("src.extractor.record_citations.date")
    def test_date_in_header(self, mock_date):
        from datetime import date as real_date
        mock_date.today.return_value = real_date(2026, 2, 18)
        mock_date.side_effect = lambda *a, **kw: real_date(*a, **kw)
        result = format_items_file({1}, ["brief.pdf"])
        assert "Date: 2026-02-18" in result


# ---------------------------------------------------------------------------
# CLI integration test
# ---------------------------------------------------------------------------

class TestExtractCitesCLI:
    def test_help(self):
        from click.testing import CliRunner
        from src.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["extract-cites", "--help"])
        assert result.exit_code == 0
        assert "Extract record citations" in result.output

    def test_no_inputs(self):
        from click.testing import CliRunner
        from src.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["extract-cites"])
        assert result.exit_code != 0
