#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Đo độ phủ dòng của phần logic tiếng Việt (tiêu chí nghiệm thu giai đoạn 3: ≥ 90%).

Chỉ đo những module chạy được không cần UNO; lớp nối với LibreOffice (nd30_writer, nd30_check_writer, nd30_dialog)
được thử bằng các phép kiểm chạy trên app thật (scripts/build-macos.sh tools), không đo ở đây.

Dùng `trace` của thư viện chuẩn nên không cần cài thêm gói nào. Chạy: scripts/coverage-vi.py [--min 90]
"""
import argparse
import sys
import trace
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHONPATH = ROOT / "extensions" / "1xvn-tools" / "pythonpath"
TESTS = ROOT / "extensions" / "1xvn-tools" / "tests"
# Module thuần Python, đo được ở đây. Những module còn lại trong vn1x cần UNO.
PURE = ["numwords.py", "vntext.py", "vnname.py", "nd30.py", "nd30_check.py", "csvsafe.py", "guides.py",
        "doctools.py", "aiconfig.py", "aicontext.py", "changeset.py"]


def executable_lines(path):
    """Các dòng thật sự sinh mã (bỏ dòng trống, chú thích, chuỗi tài liệu)."""
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    lines, stack = set(), [code]
    while stack:
        current = stack.pop()
        for _, _, line in current.co_lines():
            if line:
                lines.add(line)
        stack.extend(const for const in current.co_consts if hasattr(const, "co_lines"))
    return lines


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.discover(str(TESTS), pattern="test_*.py", top_level_dir=str(TESTS))
    result = unittest.TextTestRunner(verbosity=0, stream=open("/dev/null", "w")).run(suite)
    return result.wasSuccessful()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=90.0, help="độ phủ tối thiểu, phần trăm")
    args = ap.parse_args()
    sys.path.insert(0, str(PYTHONPATH))
    tracer = trace.Trace(count=1, trace=0)
    ok = tracer.runfunc(run_tests)
    if not ok:
        print("Có bài kiểm hỏng; sửa trước khi đo độ phủ.")
        return 1
    executed = {(Path(name).resolve(), line) for (name, line) in tracer.results().counts}
    total_hit = total_all = 0
    failures = []
    print(f"{'Module':22} {'Phủ':>7}  {'Dòng':>9}  Dòng chưa chạy")
    for name in PURE:
        path = (PYTHONPATH / "vn1x" / name).resolve()
        if not path.exists():
            failures.append(f"{name}: không thấy tệp")
            continue
        lines = executable_lines(path)
        hit = {line for line in lines if (path, line) in executed}
        missed = sorted(lines - hit)
        percent = 100.0 * len(hit) / len(lines) if lines else 100.0
        total_hit += len(hit)
        total_all += len(lines)
        shown = ", ".join(str(line) for line in missed[:8]) + ("…" if len(missed) > 8 else "")
        print(f"{name:22} {percent:6.1f}%  {len(hit):4d}/{len(lines):<4d}  {shown}")
    overall = 100.0 * total_hit / total_all if total_all else 100.0
    print(f"{'TỔNG':22} {overall:6.1f}%  {total_hit:4d}/{total_all:<4d}")
    for message in failures:
        print(f"LỖI {message}")
    if failures or overall < args.min:
        print(f"LỖI độ phủ {overall:.1f}% dưới mức yêu cầu {args.min:.0f}%.")
        return 1
    print(f"OK độ phủ logic tiếng Việt {overall:.1f}% (yêu cầu ≥ {args.min:.0f}%).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
