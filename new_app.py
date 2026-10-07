"""Shop analytics dashboard: Streamlit + SQLite + Plotly.

Every number and chart on this page comes from a SQL query against shop.db.
Open the "Show the SQL" panels to copy any query into DBeaver and run it there.
"""
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DB_PATH = Path(__file__).parent / "shop.db"

# ---------- Design tokens ----------
INK = "#1B2A41"
SLATE = "#5B6B7F"
TEXT_MUTED = "#465569"
LINE = "#E3E8EF"
PAPER = "#F6F8FB"
COBALT = "#2F5BEA"
CATEGORY_COLORS = {
    "Electronics": "#2F5BEA",
    "Furniture": "#F2A541",
    "Stationery": "#1FA896",
}
FALLBACK_COLORS = ["#8B5CF6", "#E5586B", "#64748B"]

st.set_page_config(page_title="Shop analytics", page_icon="📊", layout="wide")

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

.stApp, .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3,
.stApp button, .stApp textarea, .stTabs [data-baseweb="tab"] {{
    font-family: 'Manrope', 'Segoe UI', sans-serif;
}}
.stApp {{ background: {PAPER}; color: {INK}; }}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}
[data-testid="stToolbar"], [data-testid="stAppDeployButton"], .stAppDeployButton
    {{ display: none; }}

[data-testid="stExpander"] details {{ border: none; background: transparent; }}
[data-testid="stExpander"] summary {{ padding-left: 0; padding-right: 0; }}
[data-testid="stExpander"] summary p {{ color: {SLATE}; font-size: 0.85rem; font-weight: 700; }}
[data-testid="stExpander"] summary:hover p {{ color: {COBALT}; }}
.block-container {{ padding-top: 2.2rem; max-width: 1280px; }}

[data-testid="stSidebar"] {{ border-right: 1px solid {LINE}; }}
[data-testid="stSidebar"] h2 {{ font-size: 1.05rem; font-weight: 700; }}

.page-title {{ font-size: 2.1rem; font-weight: 800; letter-spacing: -0.02em;
               margin: 0; color: {INK}; }}
.page-sub {{ color: {SLATE}; margin: 0.25rem 0 1.4rem 0; font-size: 0.98rem; }}

.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); background: #fff;
         border: 1px solid {LINE}; border-radius: 14px; margin-bottom: 0.9rem; }}
.kpi {{ padding: 1.15rem 1.4rem; border-left: 1px solid {LINE}; }}
.kpi:first-child {{ border-left: none; }}
.kpi-label {{ color: {SLATE}; font-size: 0.85rem; font-weight: 600; }}
.kpi-value {{ font-size: 2rem; font-weight: 800; letter-spacing: -0.02em;
              font-variant-numeric: tabular-nums; line-height: 1.25; }}
.kpi-note {{ font-size: 0.8rem; color: {SLATE}; font-weight: 600; }}
.kpi-note.up {{ color: #138a6b; }}
.kpi-note.down {{ color: #cc3d4f; }}
@media (max-width: 800px) {{
    .kpis {{ grid-template-columns: repeat(2, 1fr); }}
    .kpi:nth-child(3) {{ border-left: none; }}
    .kpi:nth-child(n+3) {{ border-top: 1px solid {LINE}; }}
}}

.insight {{ color: {INK}; font-size: 1rem; margin: 0.2rem 0 1.2rem 0;
            padding-left: 0.9rem; border-left: 3px solid {COBALT}; }}

[class*="st-key-card_"] {{ background: #fff; border: 1px solid {LINE};
    border-radius: 14px; padding: 1.1rem 1.3rem 0.6rem 1.3rem; }}
.card-title {{ font-size: 1.05rem; font-weight: 700; margin: 0; }}
.card-sub {{ color: {SLATE}; font-size: 0.85rem; margin: 0.1rem 0 0.4rem 0; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 1.6rem; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 700; padding-left: 0; padding-right: 0; }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- Database helpers ----------
def connect():
    """Read-only connection, opened per query so shop.db can be rebuilt any time."""
    return sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)


@st.cache_data(show_spinner=False)
def run(sql: str, params: tuple, db_version: float) -> pd.DataFrame:
    with closing(connect()) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return run(sql, tuple(params), DB_PATH.stat().st_mtime)


def inline(sql: str, params: tuple) -> str:
    """Swap ? placeholders for literal values so the SQL can be pasted into DBeaver."""
    values = iter(params)
    return re.sub(
        r"\?",
        lambda _: (lambda v: f"'{v}'" if isinstance(v, str) else str(v))(next(values)),
        sql,
    )


def show_sql(sql: str, params: tuple):
    with st.expander("Show the SQL"):
        st.code(inline(sql, params), language="sql")


if not DB_PATH.exists():
    st.error("shop.db was not found next to app.py. Run `python create_db.py` first.")
    st.stop()

# ---------- Sidebar filters ----------
bounds = q("SELECT MIN(order_date) AS lo, MAX(order_date) AS hi FROM orders").iloc[0]
all_regions = q("SELECT DISTINCT region FROM customers ORDER BY region")["region"].tolist()
all_categories = q("SELECT DISTINCT category FROM products ORDER BY category")["category"].tolist()

with st.sidebar:
    st.markdown("## Filters")
    date_range = st.date_input(
        "Order dates",
        value=(pd.to_datetime(bounds.lo).date(), pd.to_datetime(bounds.hi).date()),
        min_value=pd.to_datetime(bounds.lo).date(),
        max_value=pd.to_datetime(bounds.hi).date(),
    )
    regions = st.multiselect("Region", all_regions, default=all_regions)
    categories = st.multiselect("Category", all_categories, default=all_categories)
    st.caption("The database is opened read-only, so nothing here can change your data.")

if len(date_range) != 2:
    st.info("Pick an end date to apply the date filter.")
    st.stop()
if not regions or not categories:
    st.info("Select at least one region and one category.")
    st.stop()

start, end = (d.isoformat() for d in date_range)

# One shared CTE: every chart below reads from this filtered "sales" table.
SALES_CTE = f"""WITH sales AS (
    SELECT o.order_id, o.order_date,
           strftime('%Y-%m', o.order_date) AS month,
           c.customer_id, c.name AS customer, c.region,
           p.name AS product, p.category,
           oi.quantity, oi.quantity * p.price AS revenue
    FROM order_items oi
    JOIN orders    o ON o.order_id    = oi.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    JOIN products  p ON p.product_id  = oi.product_id
    WHERE o.order_date BETWEEN ? AND ?
      AND c.region   IN ({",".join("?" * len(regions))})
      AND p.category IN ({",".join("?" * len(categories))})
)
"""
CTE_PARAMS = (start, end, *regions, *categories)


def query_sales(select_sql: str, extra_params: tuple = ()):
    sql = SALES_CTE + select_sql
    params = CTE_PARAMS + extra_params
    return q(sql, params), sql, params


def money(v: float) -> str:
    return f"${v:,.0f}"


def month_label(m: str) -> str:
    return pd.to_datetime(m + "-01").strftime("%b %Y")


def colour_for(category: str, i: int = 0) -> str:
    return CATEGORY_COLORS.get(category, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])


def style(fig: go.Figure, height: int = 340, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, Segoe UI, sans-serif", color=TEXT_MUTED, size=13),
        showlegend=legend,
        legend=dict(orientation="h", y=1.14, x=0, title=None, traceorder="normal"),
        hoverlabel=dict(bgcolor="white", bordercolor=LINE, font_size=13),
        bargap=0.38,
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE, title=None)
    fig.update_yaxes(gridcolor=LINE, zeroline=False, title=None)
    return fig


def card_header(title: str, sub: str):
    st.markdown(
        f'<p class="card-title">{title}</p><p class="card-sub">{sub}</p>',
        unsafe_allow_html=True,
    )


def draw(fig: go.Figure):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ---------- Header ----------
st.markdown('<h1 class="page-title">Shop analytics</h1>', unsafe_allow_html=True)
st.markdown(
    f'<p class="page-sub">Orders from {pd.to_datetime(start):%b %d} to '
    f'{pd.to_datetime(end):%b %d, %Y}, {len(regions)} of {len(all_regions)} regions</p>',
    unsafe_allow_html=True,
)

# ---------- KPIs ----------
totals, _, _ = query_sales(
    """SELECT COALESCE(SUM(revenue), 0)        AS revenue,
       COUNT(DISTINCT order_id)    AS orders,
       COUNT(DISTINCT customer_id) AS customers
FROM sales;"""
)
if totals.loc[0, "orders"] == 0:
    st.info("No orders match these filters. Widen the date range or add regions.")
    st.stop()

monthly_kpi, _, _ = query_sales(
    """SELECT month, SUM(revenue) AS revenue, COUNT(DISTINCT order_id) AS orders
FROM sales GROUP BY month ORDER BY month;"""
)
region_customers = q(
    f"SELECT COUNT(*) AS n FROM customers WHERE region IN ({','.join('?' * len(regions))})",
    tuple(regions),
).loc[0, "n"]

revenue = float(totals.loc[0, "revenue"])
orders = int(totals.loc[0, "orders"])
active = int(totals.loc[0, "customers"])
aov = revenue / orders


def delta_note(current: float, previous: float | None, label: str) -> str:
    """label looks like 'Jul vs Jun'."""
    if previous in (None, 0):
        return '<div class="kpi-note">&nbsp;</div>'
    pct = (current - previous) / previous
    if round(pct * 100) == 0:
        return f'<div class="kpi-note">{label}: no change</div>'
    cls, arrow = ("up", "▲") if pct > 0 else ("down", "▼")
    return f'<div class="kpi-note {cls}">{arrow} {abs(pct):.0%} {label}</div>'


rev_note = ord_note = aov_note = '<div class="kpi-note">&nbsp;</div>'
if len(monthly_kpi) >= 2:
    last, prev = monthly_kpi.iloc[-1], monthly_kpi.iloc[-2]
    label = f"{pd.to_datetime(last.month + '-01'):%b} vs {pd.to_datetime(prev.month + '-01'):%b}"
    rev_note = delta_note(last.revenue, prev.revenue, label)
    ord_note = delta_note(last.orders, prev.orders, label)
    aov_note = delta_note(last.revenue / last.orders, prev.revenue / prev.orders, label)

st.markdown(
    f"""
<div class="kpis">
  <div class="kpi"><div class="kpi-label">Revenue</div>
       <div class="kpi-value">{money(revenue)}</div>{rev_note}</div>
  <div class="kpi"><div class="kpi-label">Orders</div>
       <div class="kpi-value">{orders}</div>{ord_note}</div>
  <div class="kpi"><div class="kpi-label">Average order value</div>
       <div class="kpi-value">{money(aov)}</div>{aov_note}</div>
  <div class="kpi"><div class="kpi-label">Active customers</div>
       <div class="kpi-value">{active}</div>
       <div class="kpi-note">of {region_customers} in selected regions</div></div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------- Data for the charts ----------
by_month_cat, sql_month, p_month = query_sales(
    """SELECT month, category, SUM(revenue) AS revenue
FROM sales
GROUP BY month, category
ORDER BY month;"""
)
top_products, sql_prod, p_prod = query_sales(
    """SELECT product, category, SUM(revenue) AS revenue, SUM(quantity) AS units
FROM sales
GROUP BY product, category
ORDER BY revenue DESC
LIMIT 6;"""
)
by_region, sql_region, p_region = query_sales(
    f"""SELECT c.region,
       COALESCE(SUM(s.revenue), 0)  AS revenue,
       COUNT(DISTINCT s.customer_id) AS customers
FROM customers c
LEFT JOIN sales s ON s.customer_id = c.customer_id
WHERE c.region IN ({",".join("?" * len(regions))})
GROUP BY c.region
ORDER BY revenue DESC;""",
    tuple(regions),
)
running, sql_run, p_run = query_sales(
    """SELECT order_date,
       daily_revenue,
       SUM(daily_revenue) OVER (ORDER BY order_date) AS running_total
FROM (
    SELECT order_date, SUM(revenue) AS daily_revenue
    FROM sales
    GROUP BY order_date
)
ORDER BY order_date;"""
)

cat_totals = by_month_cat.groupby("category")["revenue"].sum().sort_values(ascending=False)
top_cat, top_share = cat_totals.index[0], cat_totals.iloc[0] / cat_totals.sum()
top_region = by_region.iloc[0]["region"]
st.markdown(
    f'<p class="insight">{top_cat} brings in {top_share:.0%} of revenue, '
    f"and {top_region} is the strongest region.</p>",
    unsafe_allow_html=True,
)

tab_overview, tab_customers, tab_sql = st.tabs(["Overview", "Customers", "SQL workbench"])

# ---------- Overview ----------
with tab_overview:
    left, right = st.columns([3, 2], gap="medium")

    with left:
        with st.container(key="card_monthly"):
            card_header("Revenue by month", "Stacked by product category")
            months = sorted(by_month_cat["month"].unique())
            labels = [month_label(m) for m in months]
            fig = go.Figure()
            for i, cat in enumerate(sorted(by_month_cat["category"].unique())):
                part = by_month_cat[by_month_cat.category == cat].set_index("month")["revenue"]
                fig.add_bar(
                    x=labels,
                    y=[part.get(m, 0) for m in months],
                    name=cat,
                    marker_color=colour_for(cat, i),
                    hovertemplate=f"{cat}: %{{y:$,.0f}}<extra></extra>",
                )
            month_totals = by_month_cat.groupby("month")["revenue"].sum()
            fig.add_scatter(
                x=labels,
                y=[month_totals[m] for m in months],
                text=[money(month_totals[m]) for m in months],
                mode="text",
                textposition="top center",
                textfont=dict(color=INK, size=13, family="Manrope, sans-serif"),
                showlegend=False,
                hoverinfo="skip",
            )
            fig.update_layout(barmode="stack")
            fig.update_xaxes(type="category", categoryorder="array", categoryarray=labels)
            fig.update_yaxes(
                tickprefix="$", tickformat=",", range=[0, month_totals.max() * 1.18]
            )
            draw(style(fig, 360))
            show_sql(sql_month, p_month)

    with right:
        with st.container(key="card_products"):
            card_header("Top products", "Revenue in the selected period")
            tp = top_products.sort_values("revenue")
            fig = go.Figure()
            for i, cat in enumerate(sorted(tp["category"].unique())):
                part = tp[tp.category == cat]
                fig.add_bar(
                    x=part["revenue"],
                    y=part["product"],
                    orientation="h",
                    name=cat,
                    marker_color=colour_for(cat, i),
                    text=[money(v) for v in part["revenue"]],
                    textposition="outside",
                    cliponaxis=False,
                    customdata=part[["units"]],
                    hovertemplate="%{y}: %{x:$,.0f} from %{customdata[0]} units<extra></extra>",
                )
            fig.update_layout(barmode="overlay")
            fig.update_xaxes(visible=False, range=[0, tp["revenue"].max() * 1.22])
            fig.update_yaxes(
                showgrid=False,
                categoryorder="array",
                categoryarray=tp["product"].tolist(),
            )
            draw(style(fig, 360))
            show_sql(sql_prod, p_prod)

    left, right = st.columns([2, 3], gap="medium")

    with left:
        with st.container(key="card_region"):
            card_header("Revenue by region", "Where the money comes from")
            fig = go.Figure(
                go.Bar(
                    x=by_region["region"],
                    y=by_region["revenue"],
                    marker_color=COBALT,
                    text=[money(v) for v in by_region["revenue"]],
                    textposition="outside",
                    cliponaxis=False,
                    customdata=by_region["customers"],
                    hovertemplate="%{x}: %{y:$,.0f}<br>%{customdata} ordering customers"
                    "<extra></extra>",
                )
            )
            fig.update_yaxes(visible=False, range=[0, by_region["revenue"].max() * 1.2])
            draw(style(fig, 300, legend=False))
            show_sql(sql_region, p_region)

    with right:
        with st.container(key="card_running"):
            card_header("Cumulative revenue", "A running total built with a window function")
            dates = pd.to_datetime(running["order_date"])
            pad = max((dates.max() - dates.min()) * 0.04, pd.Timedelta(days=1))
            fig = go.Figure(
                go.Scatter(
                    x=dates,
                    y=running["running_total"],
                    mode="lines+markers",
                    line=dict(color=COBALT, width=3, shape="hv"),
                    marker=dict(size=8, color="#fff", line=dict(color=COBALT, width=2)),
                    fill="tozeroy",
                    fillcolor="rgba(47, 91, 234, 0.08)",
                    customdata=running["daily_revenue"],
                    hovertemplate="%{x|%b %d, %Y}<br>Total so far: %{y:$,.0f}"
                    "<br>Added that day: %{customdata:$,.0f}<extra></extra>",
                )
            )
            fig.update_xaxes(range=[dates.min() - pad, dates.max() + pad], tickformat="%b %d")
            fig.update_yaxes(
                tickprefix="$", tickformat=",", range=[0, running["running_total"].max() * 1.12]
            )
            draw(style(fig, 300, legend=False))
            show_sql(sql_run, p_run)

# ---------- Customers ----------
with tab_customers:
    cust_sql = (
        SALES_CTE
        + f"""SELECT c.name AS customer, c.region, c.signup_date,
       COUNT(DISTINCT s.order_id)  AS orders,
       COALESCE(SUM(s.revenue), 0) AS revenue,
       MAX(s.order_date)           AS last_order
FROM customers c
LEFT JOIN sales s ON s.customer_id = c.customer_id
WHERE c.region IN ({",".join("?" * len(regions))})
GROUP BY c.customer_id
ORDER BY revenue DESC;"""
    )
    cust_params = CTE_PARAMS + tuple(regions)
    customers = q(cust_sql, cust_params)

    with st.container(key="card_customers"):
        card_header(
            "Customers",
            "Includes customers with no orders, which is what a LEFT JOIN gives you",
        )
        silent = customers[customers.orders == 0]
        if len(silent):
            st.markdown(
                f'<p class="insight">{len(silent)} customer(s) have not ordered in this '
                f"selection: {', '.join(silent.customer)}.</p>",
                unsafe_allow_html=True,
            )
        customers["signup_date"] = pd.to_datetime(customers["signup_date"])
        customers["last_order"] = pd.to_datetime(customers["last_order"])
        st.dataframe(
            customers,
            hide_index=True,
            width="stretch",
            column_config={
                "customer": st.column_config.TextColumn("Customer"),
                "region": st.column_config.TextColumn("Region"),
                "signup_date": st.column_config.DateColumn("Signed up", format="MMM D, YYYY"),
                "orders": st.column_config.NumberColumn("Orders"),
                "revenue": st.column_config.ProgressColumn(
                    "Revenue",
                    format="$%.0f",
                    min_value=0,
                    max_value=float(max(customers["revenue"].max(), 1)),
                ),
                "last_order": st.column_config.DateColumn("Last order", format="MMM D, YYYY"),
            },
        )
        show_sql(cust_sql, cust_params)

# ---------- SQL workbench ----------
EXAMPLES = {
    "Revenue by customer": """SELECT c.name, SUM(oi.quantity * p.price) AS revenue
FROM customers c
JOIN orders o       ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
JOIN products p     ON p.product_id  = oi.product_id
GROUP BY c.customer_id
ORDER BY revenue DESC;""",
    "Customers who never ordered": """SELECT c.name, c.region
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL;""",
    "Rank products by revenue": """SELECT p.name, p.category,
       SUM(oi.quantity * p.price) AS revenue,
       RANK() OVER (ORDER BY SUM(oi.quantity * p.price) DESC) AS revenue_rank
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id;""",
    "Month-over-month change": """WITH monthly AS (
    SELECT strftime('%Y-%m', o.order_date) AS month,
           SUM(oi.quantity * p.price)      AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id  = o.order_id
    JOIN products p     ON p.product_id = oi.product_id
    GROUP BY month
)
SELECT month, revenue,
       revenue - LAG(revenue) OVER (ORDER BY month) AS change_vs_prior_month
FROM monthly;""",
}


def load_example():
    st.session_state["sql"] = EXAMPLES[st.session_state["example"]]


st.session_state.setdefault("sql", next(iter(EXAMPLES.values())))

with tab_sql:
    with st.container(key="card_workbench"):
        card_header("SQL workbench", "Write any SELECT query against shop.db")
        st.selectbox(
            "Start from an example",
            list(EXAMPLES),
            key="example",
            on_change=load_example,
        )
        st.text_area("Query", key="sql", height=210)
        run_clicked = st.button("Run query", type="primary")

        if run_clicked:
            try:
                with closing(connect()) as conn:
                    result = pd.read_sql_query(st.session_state["sql"], conn)
                st.caption(f"{len(result)} row(s) returned")
                st.dataframe(result, hide_index=True, width="stretch")
                st.download_button(
                    "Download as CSV",
                    result.to_csv(index=False).encode("utf-8"),
                    file_name="query_result.csv",
                    mime="text/csv",
                )
            except Exception as err:
                if "readonly" in str(err).lower():
                    st.error("This workbench is read-only. Use DBeaver when you want to change data.")
                else:
                    st.error(f"The query failed: {err}")

        with st.expander("Tables and columns"):
            with closing(connect()) as conn:
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                for t in tables:
                    cols = ", ".join(r[1] for r in conn.execute(f"PRAGMA table_info({t})"))
                    st.markdown(f"**{t}**: {cols}")