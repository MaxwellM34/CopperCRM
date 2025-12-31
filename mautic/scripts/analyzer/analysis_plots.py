import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# -------------------------------------------------
# Global plot style
# -------------------------------------------------
sns.set_theme(
    style="whitegrid",
    context="talk",
)

# Use seaborn built-in palettes for nicer colours
SCORE_CMAP = "Blues"
ISSUE_CMAP = "magma"


def make_score_palette(n: int):
    """Palette for score distributions."""
    return sns.color_palette(SCORE_CMAP, n_colors=n)


def make_issue_palette(n: int):
    """Palette for issue frequency plots."""
    return sns.color_palette(ISSUE_CMAP, n_colors=n)


# -------------------------------------------------
# 1. Load Data
# -------------------------------------------------

num = pd.read_csv("scripts/analyzer/email_numeric_metrics.csv")
scores = pd.read_csv("scripts/analyzer/email_scores_summary.csv")
issues = pd.read_csv("scripts/analyzer/email_text_issues.csv")

df = (
    num.merge(
        scores[
            [
                "filename",
                "sample",
                "valueprop_feedback",
                "customer_reaction_feedback",
            ]
        ],
        on="filename",
        how="left",
    )
    .merge(
        issues[
            [
                "filename",
                "deliverability_fail_reason",
                "deliverability_issues",
                "clarity_fail_reason",
                "clarity_issues",
            ]
        ],
        on="filename",
        how="left",
    )
)

# Drop the TOTAL RUN / usage row for most analyses (it's an outlier)
df_no_usage = df[df["filename"] != "usage.txt"].copy()

# Ensure boolean-like fields are actually booleans
bool_cols = ["clarity_has_greeting", "clarity_has_signoff", "clarity_has_bullets"]
for col in bool_cols:
    if col in df_no_usage.columns:
        df_no_usage[col] = df_no_usage[col].astype("bool")

# -------------------------------------------------
# 2. Score Distributions
# -------------------------------------------------

score_cols = [
    "deliverability_score",
    "clarity_score",
    "valueprop_score",
    "customer_reaction_score",
]

fig, axes = plt.subplots(2, 2, figsize=(12, 8))

for ax, col in zip(axes.flatten(), score_cols):
    data = df_no_usage[col].dropna()
    if data.empty:
        ax.set_visible(False)
        continue

    # Sorted categories
    order = sorted(data.unique())
    palette = make_score_palette(len(order))

    sns.countplot(
        data=df_no_usage,
        x=col,
        hue=col,          # future-safe for seaborn 0.14+
        order=order,
        palette=palette,
        legend=False,
        ax=ax,
    )

    ax.set_title(col.replace("_", " ").title())
    ax.set_xlabel("Score")
    ax.set_ylabel("Count")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.1)

plt.tight_layout()
plt.show()

# -------------------------------------------------
# Helpers for Issue Handling
# -------------------------------------------------

def explode_issues(df_in: pd.DataFrame, col_name: str, new_col: str) -> pd.DataFrame:
    sub = df_in[["filename", col_name]].dropna().copy()
    if sub.empty:
        return pd.DataFrame(columns=["filename", new_col])

    sub[col_name] = sub[col_name].str.split(r"\s*;\s*")
    exploded = sub.explode(col_name)
    exploded = exploded.rename(columns={col_name: new_col})
    exploded[new_col] = exploded[new_col].str.strip()
    exploded = exploded[exploded[new_col] != ""]
    return exploded


# -------------------------------------------------
# 3. Issue Frequency
# -------------------------------------------------

deliv_issues_long = explode_issues(
    df_no_usage, "deliverability_issues", "deliverability_issue"
)
clarity_issues_long = explode_issues(
    df_no_usage, "clarity_issues", "clarity_issue"
)

# Ignore subject-line issues for clarity
CLARITY_ISSUES_TO_IGNORE = {"missing_subject"}
if not clarity_issues_long.empty:
    clarity_issues_long = clarity_issues_long[
        ~clarity_issues_long["clarity_issue"].isin(CLARITY_ISSUES_TO_IGNORE)
    ]

plt.figure(figsize=(13, 5))

# ---- Deliverability Issues ----
if not deliv_issues_long.empty:
    plt.subplot(1, 2, 1)
    counts = deliv_issues_long["deliverability_issue"].value_counts().head(15)
    palette = make_issue_palette(len(counts))

    sns.barplot(
        x=counts.values,
        y=counts.index,
        hue=counts.index,  # future-safe
        palette=palette,
        legend=False,
    )
    plt.title("Top Deliverability Issues")
    plt.xlabel("Count")
    plt.ylabel("Issue")

# ---- Clarity Issues ----
if not clarity_issues_long.empty:
    plt.subplot(1, 2, 2)
    counts = clarity_issues_long["clarity_issue"].value_counts().head(15)
    palette = make_issue_palette(len(counts))

    sns.barplot(
        x=counts.values,
        y=counts.index,
        hue=counts.index,
        palette=palette,
        legend=False,
    )
    plt.title("Top Clarity Issues")
    plt.xlabel("Count")
    plt.ylabel("Issue")

plt.tight_layout()
plt.show()

# -------------------------------------------------
# 4. Rank Best and Worst Emails (print only)
# -------------------------------------------------

rank_df = df_no_usage.copy()

# Replace None/NaN with 0 so totals work correctly
for col in [
    "deliverability_score",
    "clarity_score",
    "valueprop_score",
    "customer_reaction_score",
]:
    if col in rank_df.columns:
        rank_df[col] = rank_df[col].fillna(0)

rank_df["total_score"] = (
    rank_df.get("deliverability_score", 0)
    + rank_df.get("clarity_score", 0)
    + rank_df.get("valueprop_score", 0)
    + rank_df.get("customer_reaction_score", 0)
)

# Require at least one non-zero metric (avoid garbage rows)
rank_df = rank_df[rank_df["total_score"] > 0]

if not rank_df.empty:
    best = rank_df.sort_values("total_score", ascending=False).head(5)
    worst = rank_df.sort_values("total_score", ascending=True).head(5)

    print("\n" + "=" * 70)
    print("TOP 5 EMAILS BY TOTAL SCORE (best overall examples)")
    print("=" * 70)
    for _, row in best.iterrows():
        print(
            f"[Total {row['total_score']}] "
            f"D={row['deliverability_score']} "
            f"C={row['clarity_score']} "
            f"VP={row['valueprop_score']} "
            f"CR={row['customer_reaction_score']}  "
            f"{row['filename']} | preview: {row.get('sample', '')!r}"
        )

    print("\n" + "=" * 70)
    print("BOTTOM 5 EMAILS BY TOTAL SCORE (worst overall examples)")
    print("=" * 70)
    for _, row in worst.iterrows():
        print(
            f"[Total {row['total_score']}] "
            f"D={row['deliverability_score']} "
            f"C={row['clarity_score']} "
            f"VP={row['valueprop_score']} "
            f"CR={row['customer_reaction_score']}  "
            f"{row['filename']} | preview: {row.get('sample', '')!r}"
        )
