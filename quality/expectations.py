"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from datetime import datetime
from collections import defaultdict


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


class DataValidator:
    def __init__(self, rows: List[Dict[str, Any]]):
        self.rows = rows
        self.results: List[ExpectationResult] = []

    def _expect(self, name: str, severity: str, condition: bool, detail: str):
        """Ghi nhận kết quả của một điều kiện kiểm tra."""
        self.results.append(ExpectationResult(name, condition, severity, detail))

    def _expect_none(self, name: str, severity: str, violations: List[Any], detail_prefix: str = "violations"):
        """Yêu cầu không được có dòng nào vi phạm điều kiện."""
        self._expect(name, severity, len(violations) == 0, f"{detail_prefix}={len(violations)}")

    def run_all(self) -> Tuple[List[ExpectationResult], bool]:
        # E1: Kiểm tra tính sẵn sàng của dữ liệu
        self._expect("min_one_row", "halt", len(self.rows) >= 1, f"count={len(self.rows)}")

        # E2: Kiểm tra các trường bắt buộc
        self._expect_none(
            "no_empty_doc_id", "halt",
            [r for r in self.rows if not (r.get("doc_id") or "").strip()],
            "empty_doc_id_count"
        )

        # E3: Logic nghiệp vụ - Cửa sổ hoàn trả (Refund Window)
        self._expect_none(
            "refund_no_stale_14d_window", "halt",
            [r for r in self.rows if r.get("doc_id") == "policy_refund_v4" and "14 ngày làm việc" in (r.get("chunk_text") or "")]
        )

        # E4: Chất lượng - Độ dài tối thiểu của chunk
        self._expect_none(
            "chunk_min_length_8", "warn",
            [r for r in self.rows if len((r.get("chunk_text") or "")) < 8],
            "short_chunks"
        )

        # E5: Định dạng - Ngày ISO
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        self._expect_none(
            "effective_date_iso_yyyy_mm_dd", "halt",
            [r for r in self.rows if not iso_pattern.match((r.get("effective_date") or "").strip())],
            "non_iso_rows"
        )

        # E6: Logic nghiệp vụ - Markers cũ của HR Policy
        self._expect_none(
            "hr_leave_no_stale_10d_annual", "halt",
            [r for r in self.rows if r.get("doc_id") == "hr_leave_policy" and "10 ngày phép năm" in (r.get("chunk_text") or "")]
        )

        # E7: Không có effective_date trong tương lai (data sanity check)
        now = datetime.now().date()
        future_rows = []
        for r in self.rows:
            d = (r.get("effective_date") or "").strip()
            try:
                if d and datetime.fromisoformat(d).date() > now:
                    future_rows.append(r)
            except Exception:
                continue

        self._expect_none(
            "no_future_effective_date",
            "warn",
            future_rows,
            "future_dates"
        )

        # E8: Một doc_id không nên có quá nhiều version (tránh version conflict)
        versions = defaultdict(set)
        for r in self.rows:
            doc = r.get("doc_id", "")
            eff = r.get("effective_date", "")
            if doc and eff:
                versions[doc].add(eff)

        exploding_docs = [doc for doc, v in versions.items() if len(v) > 3]

        self._expect(
            "doc_id_version_explosion",
            "warn",
            len(exploding_docs) == 0,
            f"docs_with_many_versions={len(exploding_docs)}"
        )
        # E9: exported_at không được lớn hơn thời điểm hiện tại
        now_iso = datetime.now().isoformat()
        future_exported = [r for r in self.rows if r.get("exported_at") and r.get("exported_at") > now_iso]
        self._expect_none(
            "exported_at_not_in_future",
            "halt",
            future_exported,
            "future_exported_at"
        )
        halt = any(not r.passed and r.severity == "halt" for r in self.results)
        return self.results, halt


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).
    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    validator = DataValidator(cleaned_rows)
    return validator.run_all()