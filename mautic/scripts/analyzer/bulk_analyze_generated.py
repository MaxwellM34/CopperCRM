#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

from deliverability_scoring import score_deliverability
from clarity_scoring import score_structure_and_clarity
from valueprop_scorer import score_email_value_prop
from customer_reaction_scorer import score_email_customer_reaction  # NEW


def extract_subject_body(text: str) -> Tuple[str, str]:
    """
    Split raw email text into a subject line and body.

    If the first non-empty line looks like a greeting, treat the whole
    text as the body and leave subject empty. Otherwise, treat the first
    non-empty line as the subject and the rest as the body.
    """
    if not text:
        return "", ""

    lines = text.splitlines()

    first_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if line.strip():
            first_idx = i
            break

    if first_idx is None:
        return "", ""

    first_line = lines[first_idx].strip()
    lowered = first_line.lower().rstrip(",.")
    greeting_starts = (
        "hi",
        "hello",
        "dear",
        "good morning",
        "good afternoon",
        "good evening",
    )

    is_greeting = any(lowered.startswith(g) for g in greeting_starts)

    if is_greeting:
        # No subject, everything is treated as body
        return "", text.strip()

    # Otherwise, use the first non-empty line as subject
    subject = first_line
    body_lines = lines[first_idx + 1 :]

    # Drop a single blank line after the subject if present
    if body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]

    body = "\n".join(body_lines).strip()
    return subject, body


def make_body_preview(body: str, fallback: str, max_words: int = 2) -> str:
    """
    Build a short preview from the body (or fallback text if body is empty),
    using the first `max_words` words.
    """
    source = body if body.strip() else fallback
    if not source:
        return ""
    tokens = source.split()
    return " ".join(tokens[:max_words])


def analyze_email_file(path: Path) -> Dict[str, Any]:
    """
    Load a file, extract subject/body, run scoring, and return the results.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    subject, body = extract_subject_body(text)

    deliverability = score_deliverability(subject, body)
    clarity = score_structure_and_clarity(subject, body)

    # Minimal "lead" context for scoring; you can extend this later
    lead_stub: Dict[str, str] = {"filename": path.name}

    vp_score, vp_feedback = score_email_value_prop(lead_stub, body)
    cr_score, cr_feedback = score_email_customer_reaction(lead_stub, body)

    preview = make_body_preview(body, text, max_words=2)

    return {
        "filename": path.name,
        "subject": subject,
        "body_preview": preview,
        "deliverability": deliverability,
        "clarity": clarity,
        "valueprop_score": vp_score,
        "valueprop_feedback": vp_feedback,
        "customer_reaction_score": cr_score,
        "customer_reaction_feedback": cr_feedback,
    }


def analyze_directory(
    directory: Path,
    scores_csv: Optional[Path] = None,
    issues_csv: Optional[Path] = None,
    metrics_csv: Optional[Path] = None,
    extensions: tuple[str, ...] = (".txt", ".md"),
) -> None:
    """
    Walk a directory, analyze all email files, and optionally write:
      - a scores CSV (preview + final scores)
      - an issues CSV (textual issues)
      - a metrics CSV (numeric metrics)

    NOTE: Any file named 'usage.txt' is skipped and NOT analyzed.
    """
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    results: List[Dict[str, Any]] = []

    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue

        # 🔴 Skip usage.txt everywhere
        if path.name == "usage.txt":
            continue

        if path.suffix.lower() not in extensions:
            continue

        results.append(analyze_email_file(path))

    print(f"Analyzed {len(results)} emails.\n")
    for r in results:
        d = r["deliverability"]
        c = r["clarity"]
        v = r.get("valueprop_score")
        cr = r.get("customer_reaction_score")
        print(
            f"deliverability={d.get('score')} | "
            f"clarity={c.get('score')} | "
            f"valueprop={v} | "
            f"cust_reaction={cr} | "
            f"sample={r['body_preview']!r}"
        )

    # 1) Scores CSV: short preview + all scores
    if scores_csv is not None:
        with scores_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "filename",
                    "sample",
                    "deliverability_score",
                    "clarity_score",
                    "valueprop_score",
                    "valueprop_feedback",
                    "customer_reaction_score",
                    "customer_reaction_feedback",
                ],
            )
            writer.writeheader()
            for r in results:
                d = r["deliverability"]
                c = r["clarity"]
                writer.writerow(
                    {
                        "filename": r["filename"],
                        "sample": r["body_preview"],
                        "deliverability_score": d.get("score"),
                        "clarity_score": c.get("score"),
                        "valueprop_score": r.get("valueprop_score"),
                        "valueprop_feedback": r.get("valueprop_feedback") or "",
                        "customer_reaction_score": r.get("customer_reaction_score"),
                        "customer_reaction_feedback": r.get(
                            "customer_reaction_feedback"
                        )
                        or "",
                    }
                )
        print(f"Wrote scores CSV to {scores_csv}")

    # 2) Issues CSV: textual issues only
    if issues_csv is not None:
        with issues_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "filename",
                    "sample",
                    "deliverability_fail_reason",
                    "deliverability_issues",
                    "clarity_fail_reason",
                    "clarity_issues",
                    "valueprop_score",
                    "valueprop_feedback",
                    "customer_reaction_score",
                    "customer_reaction_feedback",
                ],
            )
            writer.writeheader()
            for r in results:
                d = r["deliverability"]
                c = r["clarity"]
                d_issues = d.get("issues") or []
                c_issues = c.get("issues") or []
                writer.writerow(
                    {
                        "filename": r["filename"],
                        "sample": r["body_preview"],
                        "deliverability_fail_reason": d.get("fail_reason"),
                        "deliverability_issues": "; ".join(d_issues),
                        "clarity_fail_reason": c.get("fail_reason"),
                        "clarity_issues": "; ".join(c_issues),
                        "valueprop_score": r.get("valueprop_score"),
                        "valueprop_feedback": r.get("valueprop_feedback") or "",
                        "customer_reaction_score": r.get("customer_reaction_score"),
                        "customer_reaction_feedback": r.get(
                            "customer_reaction_feedback"
                        )
                        or "",
                    }
                )
        print(f"Wrote issues CSV to {issues_csv}")

    # 3) Metrics CSV: numeric metrics (plus filename)
    if metrics_csv is not None:
        with metrics_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "filename",
                    # Deliverability metrics
                    "deliverability_score",
                    "deliverability_word_count",
                    "deliverability_link_count",
                    "deliverability_html_tag_count",
                    "deliverability_salesy_count",
                    "deliverability_cliche_count",
                    "deliverability_pressure_count",
                    "deliverability_exclamations",
                    "deliverability_caps_words",
                    "deliverability_non_ascii",
                    # Clarity metrics
                    "clarity_score",
                    "clarity_word_count",
                    "clarity_subject_word_count",
                    "clarity_paragraph_count",
                    "clarity_max_paragraph_word_count",
                    "clarity_avg_sentence_length",
                    "clarity_max_sentence_length",
                    "clarity_sentence_length_std",
                    "clarity_question_count",
                    "clarity_cta_score",
                    "clarity_has_greeting",
                    "clarity_has_signoff",
                    "clarity_has_bullets",
                    "clarity_max_line_length",
                    "clarity_subject_body_overlap",
                    "clarity_cliche_count",
                    # Value-prop
                    "valueprop_score",
                    # Customer reaction
                    "customer_reaction_score",
                ],
            )
            writer.writeheader()

            for r in results:
                d = r["deliverability"]
                c = r["clarity"]

                writer.writerow(
                    {
                        "filename": r["filename"],
                        # Deliverability
                        "deliverability_score": d.get("score"),
                        "deliverability_word_count": d.get("word_count"),
                        "deliverability_link_count": d.get("link_count"),
                        "deliverability_html_tag_count": d.get("html_tag_count"),
                        "deliverability_salesy_count": d.get("salesy_count"),
                        "deliverability_cliche_count": d.get("cliche_count"),
                        "deliverability_pressure_count": d.get("pressure_count"),
                        "deliverability_exclamations": d.get("exclamations"),
                        "deliverability_caps_words": d.get("caps_words"),
                        "deliverability_non_ascii": d.get("non_ascii"),
                        # Clarity
                        "clarity_score": c.get("score"),
                        "clarity_word_count": c.get("word_count"),
                        "clarity_subject_word_count": c.get("subject_word_count"),
                        "clarity_paragraph_count": c.get("paragraph_count"),
                        "clarity_max_paragraph_word_count": c.get(
                            "max_paragraph_word_count"
                        ),
                        "clarity_avg_sentence_length": c.get("avg_sentence_length"),
                        "clarity_max_sentence_length": c.get("max_sentence_length"),
                        "clarity_sentence_length_std": c.get("sentence_length_std"),
                        "clarity_question_count": c.get("question_count"),
                        "clarity_cta_score": c.get("cta_score"),
                        "clarity_has_greeting": int(bool(c.get("has_greeting"))),
                        "clarity_has_signoff": int(bool(c.get("has_signoff"))),
                        "clarity_has_bullets": int(bool(c.get("has_bullets"))),
                        "clarity_max_line_length": c.get("max_line_length"),
                        "clarity_subject_body_overlap": c.get(
                            "subject_body_overlap"
                        ),
                        "clarity_cliche_count": c.get("cliche_count"),
                        # Value-prop
                        "valueprop_score": r.get("valueprop_score"),
                        # Customer reaction
                        "customer_reaction_score": r.get("customer_reaction_score"),
                    }
                )
        print(f"Wrote metrics CSV to {metrics_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze email drafts for deliverability risk, structural clarity, "
            "value-prop fit, and simulated recipient reaction."
        )
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="scripts/ai-leads/generated/kraken_sdr_v3_system",
        help="Directory containing email files.",
    )
    parser.add_argument(
        "--out-scores",
        type=str,
        default="scripts/analyzer/email_scores_summary.csv",
        help="Path to scores CSV (two-word preview + scores).",
    )
    parser.add_argument(
        "--out-issues",
        type=str,
        default="scripts/analyzer/email_text_issues.csv",
        help="Path to issues CSV (textual issues only).",
    )
    parser.add_argument(
        "--out-metrics",
        type=str,
        default="scripts/analyzer/email_numeric_metrics.csv",
        help="Path to metrics CSV (numeric metrics).",
    )
    args = parser.parse_args()

    directory = Path(args.dir).resolve()
    scores_csv = Path(args.out_scores).resolve() if args.out_scores else None
    issues_csv = Path(args.out_issues).resolve() if args.out_issues else None
    metrics_csv = Path(args.out_metrics).resolve() if args.out_metrics else None

    analyze_directory(
        directory,
        scores_csv=scores_csv,
        issues_csv=issues_csv,
        metrics_csv=metrics_csv,
    )


if __name__ == "__main__":
    main()
