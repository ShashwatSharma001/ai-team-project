"""
Draw the star schema diagram and save it to docs/star_schema.png.

Run it from the project folder:
    python scripts/draw_star_schema.py
"""

import matplotlib

matplotlib.use("Agg")  # draw to a file, no window needed
import matplotlib.pyplot as plt

# Each table: (title, list of columns, x position, y position)
FACT = ("fact_complaint", [
    "complaint_id",
    "date_received_key  → dim_date",
    "date_sent_key  → dim_date",
    "product_key  → dim_product",
    "company_key  → dim_company",
    "state_key  → dim_state",
    "issue_key  → dim_issue",
    "zip_code, submitted_via, tags",
    "company_response_to_consumer",
    "is_timely, is_late, got_relief",
    "days_to_company",
], 0.5, 0.5)

DIMENSIONS = [
    ("dim_date", ["date_key", "full_date", "year, quarter, month",
                  "year_month, day_name", "is_weekend"], 0.13, 0.82),
    ("dim_product  (SCD Type 2)", ["product_key", "product_family", "product, sub_product",
                                   "effective_from, effective_to", "is_current"], 0.87, 0.82),
    ("dim_company", ["company_key", "company_name", "peer_group", "short_name"], 0.13, 0.18),
    ("dim_state", ["state_key", "state_code", "region", "is_td_footprint"], 0.87, 0.18),
    ("dim_issue", ["issue_key", "issue", "sub_issue"], 0.5, 0.06),
]

FACT_COLOUR = "#1f77b4"
DIM_COLOUR = "#7f7f7f"


def draw_table(ax, title, columns, x, y, colour):
    """Draw one table as a box: title on top, one column name per line."""
    text = "\n".join(columns)
    ax.text(x, y, text, ha="center", va="top", fontsize=8.5, family="monospace",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor=colour, linewidth=1.5))
    ax.text(x, y + 0.012, title, ha="center", va="bottom", fontsize=10, weight="bold",
            color="white", bbox=dict(boxstyle="round,pad=0.35", facecolor=colour, edgecolor=colour))


def main():
    fig, ax = plt.subplots(figsize=(12, 8.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.1, 1.0)
    ax.axis("off")

    # Lines from the fact table to each dimension (drawn first, so boxes sit on top).
    fact_x, fact_y = FACT[2], FACT[3] - 0.12
    for _, _, x, y in DIMENSIONS:
        ax.plot([fact_x, x], [fact_y, y - 0.06], color="#bbbbbb", linewidth=1.5, zorder=0)

    draw_table(ax, FACT[0], FACT[1], FACT[2], FACT[3] + 0.14, FACT_COLOUR)
    for title, columns, x, y in DIMENSIONS:
        draw_table(ax, title, columns, x, y, DIM_COLOUR)

    ax.set_title("Star schema: one fact row per complaint, linked to 5 dimensions",
                 fontsize=13, weight="bold", pad=12)
    fig.savefig("docs/star_schema.png", dpi=150, bbox_inches="tight")
    print("saved docs/star_schema.png")


if __name__ == "__main__":
    main()
