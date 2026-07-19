# -*- coding: utf-8 -*-
import argparse
import datetime as dt
import glob
import os
import subprocess
import sys
from pathlib import Path


SAVE_ROOT = r"G:\マイドライブ\TDnet_Downloads"

KEYWORDS = [
    "価格交渉",
    "増産",
    "価格改定",
    "価格転嫁",
    "値上",
    "想定以上",
    "上方修正",
    "下方修正",
    "想定以下",
    "未達",
    "大幅",
    "計画を上",
    "計画を下",
    "計画以",
    "需要回復",
    "需要の回復",
    "需要が増",
    "需要が低",
    "悪化",
    "グローバルニッチトップ",
    "トップシェア",
    "シェア拡大",
    "レアアース",
]


def find_one(pattern: str, exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    matches = [
        p
        for p in glob.glob(pattern)
        if Path(p).name not in exclude and Path(p).is_file()
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one match for {pattern}, got {matches}")
    return matches[0]


def run_step(args: list[str], log_file: Path) -> None:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    with log_file.open("a", encoding="utf-8", errors="replace") as f:
        f.write("\n$ " + " ".join(args) + "\n")
        f.flush()
        subprocess.run(args, stdout=f, stderr=subprocess.STDOUT, check=True, env=env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TDnet automatic local runner")
    parser.add_argument("target", nargs="?", help="Target date, YYYYMMDD. Defaults to today.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    target = args.target or dt.datetime.now().strftime("%Y%m%d")
    run_id = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"auto_local_{target}_{run_id}.log"

    print(f"TDnet auto run: {target}")
    print(f"Log: {log_file}")

    with log_file.open("w", encoding="utf-8", errors="replace") as f:
        f.write("============================================\n")
        f.write(f" TDnet auto run: {target}\n")
        f.write(f" Start: {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write("============================================\n")

    try:
        downloader = find_one("*_tdnet*.py", exclude={Path(__file__).name})
        analyzer = find_one("*フリーワード*.py", exclude={Path(__file__).name})

        run_step(
            [
                sys.executable,
                "-u",
                downloader,
                "--target",
                target,
                "--save-root",
                SAVE_ROOT,
            ],
            log_file,
        )
        run_step(
            [
                sys.executable,
                "-u",
                analyzer,
                "analyze",
                "--target",
                target,
                "--save-root",
                SAVE_ROOT,
                "--keywords",
                *KEYWORDS,
            ],
            log_file,
        )
        run_step(
            [
                sys.executable,
                "-u",
                analyzer,
                "distribute",
                "--target",
                target,
                "--save-root",
                SAVE_ROOT,
                "--no-stop-on-empty-meta",
            ],
            log_file,
        )
    except Exception as exc:
        with log_file.open("a", encoding="utf-8", errors="replace") as f:
            f.write("\n============================================\n")
            f.write(f" FAILED: {exc}\n")
            f.write(f" End: {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write("============================================\n")
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    with log_file.open("a", encoding="utf-8", errors="replace") as f:
        f.write("\n============================================\n")
        f.write(f" Done: {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write("============================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
