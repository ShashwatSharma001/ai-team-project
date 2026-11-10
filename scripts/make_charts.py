"""
Make one chart per client question and save them to charts/.

Run it from the project folder, AFTER building the star schema:
    python scripts/make_charts.py

For each chart the script:
1. runs one SQL file from sql/ in BigQuery (read-only, nothing is changed)
2. draws the result with Matplotlib
3. writes a title that states the insight, using numbers from the result
4. prints the client question at the bottom of the chart

Colours: TD (the client) in blue, the peer banks in grey.
"""

import os

import matplotlib

matplotlib.use("Agg")  # draw to files, no window needed
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from google.cloud import bigquery

TD_COLOUR = "#2a78d6"
TD_LIGHT = "#a9c8ef"    # lighter blue, for TD's raw monthly line
PEER_COLOUR = "#a3a3a0"
TEXT_COLOUR = "#0b0b0b"
MUTED_COLOUR = "#52514e"
GRID_COLOUR = "#e6e6e3"

SOURCE_NOTE = (
    "Source: CFPB Consumer Complaint Database, complaints received 2016-2018. "
    "Peers = Wells Fargo, Bank of America, JPMorgan Chase, Citibank, Capital One, "
    "U.S. Bank, PNC, Citizens."
)


# ---------- helpers ----------

def run_sql(client, path):
    """Run one .sql file in BigQuery and return the result as a DataFrame."""
    with open(path) as file:
        sql = file.read()
    return client.query(sql).to_dataframe(create_bqstorage_client=False)


def style_axes(ax, grid_axis="x"):
    """Quiet axes: no box, light grid lines, grey tick labels."""
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID_COLOUR)
    ax.tick_params(colors=MUTED_COLOUR, length=0)
    ax.grid(axis=grid_axis, color=GRID_COLOUR, linewidth=0.8)
    ax.set_axisbelow(True)


def add_titles(fig, title, subtitle):
    """Insight title (bold) and a one-line explanation under it."""
    fig.text(0.01, 0.97, title, fontsize=14, weight="bold", color=TEXT_COLOUR, ha="left", va="top")
    fig.text(0.01, 0.915, subtitle, fontsize=10.5, color=MUTED_COLOUR, ha="left", va="top")


def add_footer_and_save(fig, question, filename):
    """Print the client question at the bottom, then save the chart."""
    fig.text(0.01, 0.055, "Client question: " + question,
             fontsize=10.5, color=TEXT_COLOUR, ha="left", style="italic")
    fig.text(0.01, 0.02, SOURCE_NOTE, fontsize=8, color=MUTED_COLOUR, ha="left")
    path = os.path.join("charts", filename)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved {path}")


def grouped_barh(ax, labels, td_values, peer_values, td_text, peer_text):
    """Horizontal bars: TD (blue) and peers (grey) side by side for each label.

    td_text / peer_text are the value labels written at the end of each bar.
    The first label is drawn at the top.
    """
    y = np.arange(len(labels))
    height = 0.38
    ax.barh(y - height / 2, td_values, height, color=TD_COLOUR, label="TD Bank")
    ax.barh(y + height / 2, peer_values, height, color=PEER_COLOUR, label="Peers (8 banks)")
    for i in range(len(labels)):
        ax.text(td_values[i], y[i] - height / 2, " " + td_text[i],
                va="center", fontsize=8.5, color=TEXT_COLOUR)
        ax.text(peer_values[i], y[i] + height / 2, " " + peer_text[i],
                va="center", fontsize=8.5, color=MUTED_COLOUR)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, color=TEXT_COLOUR)
    ax.invert_yaxis()  # first label at the top
    ax.legend(frameon=False, loc="lower right")
    style_axes(ax, grid_axis="x")


def month_axis(ax):
    """Date axis with a label every 6 months, e.g. 'Jan 2017', so labels do not overlap."""
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def td_and_peer_columns(df, index_col, value_col):
    """Turn rows (one per product + group) into columns 'Client' and 'Peer'.

    Only keeps rows where BOTH TD and the peers have a value.
    """
    wide = df.pivot(index=index_col, columns="peer_group", values=value_col)
    return wide.dropna().astype(float)


# ---------- one function per chart ----------

def chart_1_products_and_trend(client):
    df = run_sql(client, "sql/01_products_and_trend.sql")

    # Left: share of each group's complaints by product, all 3 years together.
    totals = df.groupby(["product_family", "peer_group"])["complaints"].sum().unstack().fillna(0)
    share = (100 * totals / totals.sum()).sort_values("Client", ascending=False)

    # Right: complaints per year, as an index (2016 = 100) so both groups fit one axis.
    yearly = df.groupby(["year", "peer_group"])["complaints"].sum().unstack().astype(float)
    index = 100 * yearly / yearly.iloc[0]
    td_change = index["Client"].iloc[-1] - 100
    peer_change = index["Peer"].iloc[-1] - 100
    top_product = share.index[0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6.5), gridspec_kw={"width_ratios": [1.4, 1]})
    fig.subplots_adjust(top=0.8, bottom=0.17, wspace=0.45)

    grouped_barh(
        ax1, list(share.index), share["Client"].values, share["Peer"].values,
        [f"{v:.0f}%" for v in share["Client"]], [f"{v:.0f}%" for v in share["Peer"]],
    )
    ax1.set_title("Share of each group's complaints, by product", fontsize=11, color=TEXT_COLOUR, loc="left")
    ax1.set_xlabel("% of complaints", color=MUTED_COLOUR)

    years = list(index.index)
    ax2.plot(years, index["Client"], color=TD_COLOUR, linewidth=2, marker="o", markersize=8, label="TD Bank")
    ax2.plot(years, index["Peer"], color=PEER_COLOUR, linewidth=2, marker="o", markersize=8,
             label="Peers (8 banks)")
    ax2.text(years[-1], index["Client"].iloc[-1], f"  {index['Client'].iloc[-1]:.0f}", va="center",
             color=TEXT_COLOUR)
    ax2.text(years[-1], index["Peer"].iloc[-1], f"  {index['Peer'].iloc[-1]:.0f}", va="center",
             color=MUTED_COLOUR)
    ax2.set_xticks(years)
    ax2.set_title("Complaints per year (2016 = 100)", fontsize=11, color=TEXT_COLOUR, loc="left")
    ax2.legend(frameon=False, loc="upper left")
    style_axes(ax2, grid_axis="y")

    direction = "fell" if peer_change < 0 else "rose"
    add_titles(
        fig,
        f"TD's complaints grew {td_change:.0f}% from 2016 to 2018, while peers' {direction} "
        f"{abs(peer_change):.0f}%",
        f"{top_product} is TD's biggest source of complaints ({share['Client'].iloc[0]:.0f}% vs "
        f"{share['Peer'].iloc[0]:.0f}% for peers). Mortgage is a much smaller share for TD than for peers.",
    )
    add_footer_and_save(
        fig, "Which products create the most complaints, and is it getting worse? (Where does the pain come from?)",
        "01_products_and_trend.png",
    )


def chart_2_states(client):
    df = run_sql(client, "sql/02_states_per_month.sql").head(10)  # top 10 states for TD

    top3 = df.head(3)
    top3_td = top3["td_share_pct"].sum()
    top3_peer = top3["peer_share_pct"].sum()

    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.subplots_adjust(top=0.8, bottom=0.17)
    td_labels = [f"{s:.0f}%  ({m:.0f} a month)" for s, m in zip(df["td_share_pct"], df["td_complaints_per_month"])]
    grouped_barh(
        ax, list(df["state_code"]), df["td_share_pct"].astype(float).values,
        df["peer_share_pct"].astype(float).values,
        td_labels, [f"{v:.0f}%" for v in df["peer_share_pct"]],
    )
    ax.set_xlabel("% of each group's complaints", color=MUTED_COLOUR)

    add_titles(
        fig,
        f"{', '.join(top3['state_code'])} produce {top3_td:.0f}% of TD's complaints, "
        f"about {top3_td / top3_peer:.0f}x their share for peers",
        "Top 10 states for TD. Labels show TD's share and its average complaints per month. "
        "TD's branches are on the East Coast, so its complaints are concentrated there.",
    )
    add_footer_and_save(
        fig, "Which states complain most per month? (Where should staff go?)",
        "02_states_per_month.png",
    )


def chart_3_late_responses(client):
    df = run_sql(client, "sql/03_late_responses_by_product.sql")
    late_pct = td_and_peer_columns(df, "product_family", "late_pct").sort_values("Peer", ascending=False)

    td_rows = df[df["peer_group"] == "Client"]
    peer_rows = df[df["peer_group"] == "Peer"]
    td_late = int(td_rows["late_responses"].sum())
    td_total = int(td_rows["complaints"].sum())
    peer_rate = 100 * peer_rows["late_responses"].sum() / peer_rows["complaints"].sum()

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.subplots_adjust(top=0.8, bottom=0.18)
    grouped_barh(
        ax, list(late_pct.index), late_pct["Client"].values, late_pct["Peer"].values,
        [f"{v:.1f}%" for v in late_pct["Client"]], [f"{v:.1f}%" for v in late_pct["Peer"]],
    )
    ax.set_xlabel("% of complaints answered late", color=MUTED_COLOUR)

    times = "time" if td_late == 1 else "times"
    add_titles(
        fig,
        f"TD answered late only {td_late} {times} in {td_total:,} complaints; "
        f"peers were late {peer_rate:.1f}% of the time",
        "Late = the company did not respond within the CFPB's time limit. "
        "Products with fewer than 100 complaints are left out.",
    )
    add_footer_and_save(
        fig, "How often do companies respond late, by product? (Where are we slow?)",
        "03_late_responses_by_product.png",
    )


def chart_4_relief(client):
    df = run_sql(client, "sql/04_relief_vs_explanation.sql")
    relief = td_and_peer_columns(df, "product_family", "relief_pct").sort_values("Client", ascending=False)

    # Overall relief rate per group, weighted by number of complaints.
    df["relief_count"] = df["relief_pct"].astype(float) * df["complaints"] / 100
    overall = df.groupby("peer_group")[["relief_count", "complaints"]].sum()
    td_rate = 100 * overall.loc["Client", "relief_count"] / overall.loc["Client", "complaints"]
    peer_rate = 100 * overall.loc["Peer", "relief_count"] / overall.loc["Peer", "complaints"]

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.subplots_adjust(top=0.8, bottom=0.18)
    grouped_barh(
        ax, list(relief.index), relief["Client"].values, relief["Peer"].values,
        [f"{v:.0f}%" for v in relief["Client"]], [f"{v:.0f}%" for v in relief["Peer"]],
    )
    ax.set_xlabel("% of complaints closed with relief", color=MUTED_COLOUR)

    title = f"TD gives relief in {td_rate:.0f}% of complaints vs {peer_rate:.0f}% for peers"
    if (relief["Client"] > relief["Peer"]).all():
        title += ", and more often in every product"
    add_titles(
        fig, title,
        "Relief = money back or a fix (monetary or non-monetary relief), not just an explanation.",
    )
    add_footer_and_save(
        fig,
        "How often does TD give relief vs only an explanation, compared with peers? (What fixes things?)",
        "04_relief_vs_explanation.png",
    )


def chart_5_category_change(client):
    df = run_sql(client, "sql/05_scd2_category_change.sql")
    df["month"] = pd.to_datetime(df["year_month"] + "-01")

    # Share of each group's monthly complaints in the credit-reporting family
    # (old label + new label added together, thanks to product_family in dim_product).
    credit = df[df["product_family"] == "Credit reporting"]
    share = credit.groupby(["month", "peer_group"])["pct_of_group_month"].sum().unstack().fillna(0).astype(float)

    change_month = pd.Timestamp("2017-04-01")
    before = share[share.index < change_month].mean()
    after = share[share.index > change_month].mean()

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.subplots_adjust(top=0.8, bottom=0.18)
    ax.plot(share.index, share["Client"], color=TD_COLOUR, linewidth=2, label="TD Bank")
    ax.plot(share.index, share["Peer"], color=PEER_COLOUR, linewidth=2, label="Peers (8 banks)")
    ax.axvline(pd.Timestamp("2017-04-24"), color=MUTED_COLOUR, linestyle="--", linewidth=1)
    ax.text(pd.Timestamp("2017-05-10"), 1.5, "24 Apr 2017: CFPB renames\nproduct categories",
            fontsize=9, color=MUTED_COLOUR, va="bottom")
    ax.set_ylabel("% of the group's complaints that month", color=MUTED_COLOUR)
    ax.legend(frameon=False, loc="upper left")
    month_axis(ax)
    style_axes(ax, grid_axis="y")

    add_titles(
        fig,
        "Credit-reporting complaints rose for TD and peers from early 2017, before and after the rename",
        f"Old and new labels joined into one line (SCD Type 2). Average month before vs after: "
        f"TD {before['Client']:.1f}% -> {after['Client']:.1f}%, peers {before['Peer']:.1f}% -> {after['Peer']:.1f}%. "
        "Not a TD-only problem.",
    )
    add_footer_and_save(
        fig,
        "How did complaint patterns shift when product categories were reorganised? "
        "(Did the change hide or reveal problems?)",
        "05_scd2_category_change.png",
    )


def chart_6_correlation(client):
    df = run_sql(client, "sql/06_correlation_volume_vs_relief.sql")
    df["month"] = pd.to_datetime(df["year_month"] + "-01")
    volume = df["complaints"].astype(float)
    relief = df["relief_pct"].astype(float)
    r = float(df["corr_volume_vs_relief"].iloc[0])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [1.3, 1]})
    fig.subplots_adjust(top=0.8, bottom=0.18, wspace=0.3)

    # Left: monthly volume and its 3-month rolling average (engineered feature).
    ax1.plot(df["month"], volume, color=TD_LIGHT, linewidth=1.5, label="Complaints per month")
    ax1.plot(df["month"], df["rolling_3m_complaints"].astype(float), color=TD_COLOUR, linewidth=2,
             label="3-month rolling average")
    ax1.set_title("TD complaints per month", fontsize=11, color=TEXT_COLOUR, loc="left")
    ax1.legend(frameon=False, loc="upper left")
    month_axis(ax1)
    style_axes(ax1, grid_axis="y")

    # Right: one dot per month, with a straight trend line.
    slope, intercept = np.polyfit(volume, relief, 1)
    xs = np.linspace(volume.min(), volume.max(), 50)
    ax2.scatter(volume, relief, s=45, color=TD_COLOUR, edgecolor="white", linewidth=1.5, zorder=3)
    ax2.plot(xs, slope * xs + intercept, color=MUTED_COLOUR, linewidth=1.5, linestyle="--")
    ax2.set_title("Each dot = one month", fontsize=11, color=TEXT_COLOUR, loc="left")
    ax2.set_xlabel("TD complaints that month", color=MUTED_COLOUR)
    ax2.set_ylabel("% closed with relief", color=MUTED_COLOUR)
    style_axes(ax2, grid_axis="y")

    add_titles(
        fig,
        f"In busier months, TD gives relief less often (correlation r = {r:.2f})",
        "This may not be cause and effect: the product mix changed at the same time "
        "(more credit-reporting complaints, which get relief less often).",
    )
    add_footer_and_save(
        fig, "When TD gets more complaints in a month, does it give relief less often? (Correlation)",
        "06_correlation_volume_vs_relief.png",
    )


def main():
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    bq = config["bigquery"]
    client = bigquery.Client(project=bq["project"], location=bq["location"])

    os.makedirs("charts", exist_ok=True)
    chart_1_products_and_trend(client)
    chart_2_states(client)
    chart_3_late_responses(client)
    chart_4_relief(client)
    chart_5_category_change(client)
    chart_6_correlation(client)


if __name__ == "__main__":
    main()
