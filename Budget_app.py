# NEw Code starts from here.

import os
import pandas as pd
import streamlit as st
from datetime import date
import plotly.express as px
from supabase import create_client, Client


st.set_page_config(page_title="Budget Tracker", layout="wide")

# --- Password Protection ---
PASSWORD = "abhi2024"  # Change this to your own password

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Budget Tracker Login")
        password = st.text_input("Enter password", type="password")
        if st.button("Login"):
            if password == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password. Try again.")
        st.stop()

check_password()

CATEGORIES = [
    "Groceries",
    "Personal Care",
    "Dining",
    "Shopping",
    "Rent",
    "Utilities(Gas+Electric)",
    "Fuel",
    "Phone and Wifi",
    "Car Insurance",
    "Travel",
    "Miscellaneous"
]


# --- Supabase client (reads credentials from Streamlit Cloud secrets) ---
# NOTE: Switched from local CSV files to Supabase cloud storage.
# Previous local-file constants kept for reference:
# BUDGET_FILE   = "budgets.csv"
# TXN_FILE      = "transactions.csv"
# SETTINGS_FILE = "settings.csv"

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()


def load_budgets() -> pd.DataFrame:
    # NOTE: Original local-file loader (kept for reference):
    # if os.path.exists(BUDGET_FILE):
    #     df = pd.read_csv(BUDGET_FILE)
    #     existing = set(df["category"].tolist())
    #     missing = [c for c in CATEGORIES if c not in existing]
    #     if missing:
    #         df = pd.concat([df, pd.DataFrame(...)], ignore_index=True)
    #     return df.sort_values("category").reset_index(drop=True)
    # return pd.DataFrame({"category": CATEGORIES, "monthly_budget": [0.0] * len(CATEGORIES)})
    res = supabase.table("budgets").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)[["category", "monthly_budget"]]
        existing = set(df["category"].tolist())
        missing = [c for c in CATEGORIES if c not in existing]
        if missing:
            df = pd.concat(
                [df, pd.DataFrame({"category": missing, "monthly_budget": [0.0] * len(missing)})],
                ignore_index=True,
            )
        return df.sort_values("category").reset_index(drop=True)
    return pd.DataFrame({"category": CATEGORIES, "monthly_budget": [0.0] * len(CATEGORIES)})


def save_budgets(df: pd.DataFrame) -> None:
    # NOTE: Original local-file saver (kept for reference):
    # df.to_csv(BUDGET_FILE, index=False)
    for _, row in df.iterrows():
        supabase.table("budgets").upsert(
            {"category": row["category"], "monthly_budget": float(row["monthly_budget"])},
            on_conflict="category",
        ).execute()


def load_txns() -> pd.DataFrame:
    # NOTE: Original local-file loader (kept for reference):
    # if os.path.exists(TXN_FILE):
    #     df = pd.read_csv(TXN_FILE)
    #     df["date"] = pd.to_datetime(df["date"]).dt.date
    #     return df
    # return pd.DataFrame(columns=["date", "category", "amount", "note"])
    res = supabase.table("transactions").select("*").order("date", desc=False).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        keep_cols = [c for c in ["id", "date", "category", "amount", "note"] if c in df.columns]
        return df[keep_cols]
    return pd.DataFrame(columns=["id", "date", "category", "amount", "note"])


def save_txn(txn_date, category, amount, note) -> None:
    supabase.table("transactions").insert(
        {"date": str(txn_date), "category": category, "amount": float(amount), "note": note}
    ).execute()


def delete_txn(txn_id) -> None:
    supabase.table("transactions").delete().eq("id", txn_id).execute()


def month_filter(df: pd.DataFrame, y: int, m: int) -> pd.DataFrame:
    if df.empty:
        return df
    d = pd.to_datetime(df["date"])
    return df[(d.dt.year == y) & (d.dt.month == m)].copy()


def load_income() -> float:
    # NOTE: Original local-file loader retained for reference.
    # if os.path.exists(SETTINGS_FILE):
    #     s = pd.read_csv(SETTINGS_FILE)
    #     if "monthly_income" in s.columns and len(s) > 0:
    #         try:
    #             return float(s.loc[0, "monthly_income"])
    #         except Exception:
    #             return 0.0
    res = supabase.table("settings").select("*").execute()
    if res.data:
        return float(res.data[0].get("monthly_income", 0.0) or 0.0)
    return 0.0


def save_income(value: float) -> None:
    # NOTE: Original local-file saver retained for reference.
    # pd.DataFrame([{"monthly_income": float(value)}]).to_csv(SETTINGS_FILE, index=False)
    res = supabase.table("settings").select("*").execute()
    if res.data:
        supabase.table("settings").update({"monthly_income": float(value)}).eq("id", res.data[0]["id"]).execute()
    else:
        supabase.table("settings").insert({"monthly_income": float(value)}).execute()

#------------Title-------------------------
st.title("Your Personal Budget Tracker")

# --- Sidebar: month selection ---
today = date.today()
colA, colB = st.sidebar.columns(2)
year = colA.number_input("Year", min_value=2000, max_value=2100, value=today.year, step=1)
month = colB.number_input("Month", min_value=1, max_value=12, value=today.month, step=1)

# NOTE: Added category filter in sidebar so user can focus on selected categories only.
# selected_categories = st.sidebar.multiselect("Filter categories", options=CATEGORIES, default=CATEGORIES)
selected_categories = st.sidebar.multiselect(
    "Filter categories",
    options=CATEGORIES,
    default=CATEGORIES,
    help="Pick one or more categories to filter tables, KPIs, and charts.",
)

# NOTE: If user clears all selections, fallback to all categories.
active_categories = selected_categories if selected_categories else CATEGORIES

st.sidebar.markdown("---")
# NOTE: Updated storage note after switching back to Supabase.
# st.sidebar.caption("Data is stored locally in budgets.csv, transactions.csv, settings.csv")
st.sidebar.caption("Data is stored in Supabase cloud database.")


# --- Income ---
st.subheader(" Set Monthly Income (Mohtly Salary)")

# This line 187 through 193 was replaced; initially it was current_income = load_income()
try:
    current_income = load_income()
except Exception as e:
    st.error("Couldn't reach the database. If this is a free Supabase project, "
             "it may be paused — restore it from the dashboard and refresh.")
    st.exception(e)  # remove once you've confirmed the cause
    st.stop()
income_col1, income_col2 = st.columns([1, 3])
monthly_income = income_col1.number_input(
    "Monthly income ($)",
    min_value=0.0,
    step=100.0,
    format="%.2f",
    value=float(current_income),
    help="Enter your monthly salary/income (use take-home amount if you want 'true' remaining cash).",
)
if income_col2.button("Save income"):
    save_income(monthly_income)
    st.success("Income saved!")

st.markdown("---")


# --- Load data ---
budgets = load_budgets()
txns = load_txns()
txns_m = month_filter(txns, int(year), int(month))

# NOTE: Added month-level filtered transactions based on selected categories.
# txns_m_filtered = txns_m
txns_m_filtered = txns_m[txns_m["category"].isin(active_categories)].copy()

# --- Budgets editor ---
st.subheader("Set Monthly Budgets")
edited = st.data_editor(
    budgets,
    num_rows="fixed",
    use_container_width=True,
    hide_index=True,
    column_config={
        "category": st.column_config.TextColumn(disabled=True),
        "monthly_budget": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="$%.2f"),
    },
)
if st.button("Save budgets"):
    save_budgets(edited)
    st.success("Budgets saved!")

st.markdown("---")


# --- Add transaction ---
st.subheader("Add Transaction")
with st.form("add_txn", clear_on_submit=True):
    c1, c2, c3 = st.columns([1, 1, 1])
    txn_date = c1.date_input("Date", value=today)
    cat = c2.selectbox("Category", CATEGORIES)
    amt = c3.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
    note = st.text_input("Note (optional)", value="")
    submitted = st.form_submit_button("Add")

if submitted:
    if amt <= 0:
        st.error("Amount must be greater than 0.")
    else:
        # NOTE: Original local append/save retained for reference.
        # new_row = pd.DataFrame([{"date": txn_date, "category": cat, "amount": float(amt), "note": note}])
        # txns = pd.concat([txns, new_row], ignore_index=True)
        # save_txns(txns)
        save_txn(txn_date, cat, amt, note)
        st.success("Transaction added!")
        st.rerun()


# reload month view after add
txns = load_txns()
txns_m = month_filter(txns, int(year), int(month))

# NOTE: Keep month view in sync with category filter after adding transactions.
# txns_m_filtered = txns_m
txns_m_filtered = txns_m[txns_m["category"].isin(active_categories)].copy()

st.markdown("---")


# --- Summary ---
st.subheader(f"Summary For {int(year)}-{int(month):02d}")

# NOTE: Summary now respects selected categories.
# spent = (
#     txns_m.groupby("category")["amount"].sum()
#     .reindex(CATEGORIES)
#     .fillna(0.0)
#     .reset_index()
#     .rename(columns={"amount": "spent"})
# )
spent = (
    txns_m_filtered.groupby("category")["amount"].sum()
    .reindex(active_categories)
    .fillna(0.0)
    .reset_index()
    .rename(columns={"amount": "spent"})
)

# NOTE: Budget rows also scoped to selected categories.
# budgets_latest = load_budgets().set_index("category").reindex(CATEGORIES).fillna(0.0).reset_index()
budgets_latest = (
    load_budgets().set_index("category").reindex(active_categories).fillna(0.0).reset_index()
)
summary = budgets_latest.merge(spent, on="category", how="left").fillna({"spent": 0.0})
summary["remaining_in_category"] = summary["monthly_budget"] - summary["spent"]
summary["status"] = summary["remaining_in_category"].apply(lambda x: "Over" if x < 0 else "OK")


# Totals
total_budget = float(summary["monthly_budget"].sum())
total_spent = float(summary["spent"].sum())


# Income-based rollups
income = float(load_income())
remaining_after_spend = income - total_spent
planned_remaining_after_budget = income - total_budget
over_under_budget_vs_spend = total_budget - total_spent


# KPI row
k1, k2, k3, k4 = st.columns(4)
k1.metric("Monthly income", f"${income:,.2f}")
k2.metric("Total budget (planned)", f"${total_budget:,.2f}")
k3.metric("Total spent (actual)", f"${total_spent:,.2f}")
k4.metric("Remaining after spending", f"${remaining_after_spend:,.2f}")

k5, k6, k7 = st.columns(3)
k5.metric("Planned remaining after budget", f"${planned_remaining_after_budget:,.2f}")
k6.metric("Under/Over budget so far (budget - spent)", f"${over_under_budget_vs_spend:,.2f}")
k7.metric("Gap to income plan (remaining - planned remaining)", f"${(remaining_after_spend - planned_remaining_after_budget):,.2f}")



# Table + chart
c1, c2 = st.columns([1.2, 1])
with c1:
    st.write("Spent vs Budget by category")
    st.dataframe(
        summary[["category", "monthly_budget", "spent", "remaining_in_category", "status"]],
        use_container_width=True,
        hide_index=True,
    )

with c2:
    chart_df = summary[["category", "spent", "monthly_budget"]]
    chart_long = chart_df.melt(
        id_vars="category",
        value_vars=["spent", "monthly_budget"],
        var_name="Type",
        value_name="Amount"
    )
    fig = px.bar(
        chart_long,
        x="category",
        y="Amount",
        color="Type",
        barmode="group",
        title="Budget vs Spent by Category"
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- Transactions table ---
st.subheader("Transactions (this month)")

# NOTE: Transactions table now uses category-filtered month data.
# if txns_m.empty:
#     st.info("No transactions recorded for this month yet.")
if txns_m_filtered.empty:
    st.info("No transactions recorded for this month for the selected category filter.")
else:
    # NOTE: Preserve original reset logic while applying category filter.
    # txns_m = txns_m.reset_index()
    txns_m_filtered = txns_m_filtered.reset_index()
    for i, row in txns_m_filtered.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 1])
        col1.write(row["date"])
        col2.write(row["category"])
        col3.write(f"${row['amount']}")
        col4.write(row["note"])
        if col5.button("Delete", key=i):
            # NOTE: Original local delete retained for reference.
            # txns_all = load_txns()
            # txns_all = txns_all.drop(row["index"])
            # save_txns(txns_all)
            # st.rerun()
            if "id" in row and pd.notna(row["id"]):
                delete_txn(row["id"])
                st.rerun()
            else:
                st.error("Could not delete row because transaction id is missing.")

st.markdown("---")

# --- Import transactions from CSV (optional) ---
st.subheader("5) Import transactions from CSV (optional)")
st.caption("CSV columns required: date, category, amount, note (note optional). Category must match one of the app categories.")
uploaded = st.file_uploader("Upload CSV", type=["csv"])
if uploaded is not None:
    try:
        imp = pd.read_csv(uploaded)
        required = {"date", "category", "amount"}
        if not required.issubset(set(imp.columns)):
            st.error(f"CSV must contain columns: {sorted(list(required))} (note optional).")
        else:
            if "note" not in imp.columns:
                imp["note"] = ""
            imp["date"] = pd.to_datetime(imp["date"]).dt.date
            imp["category"] = imp["category"].astype(str).str.strip()
            bad = imp[~imp["category"].isin(CATEGORIES)]
            if not bad.empty:
                st.error("Some rows have invalid categories. Fix these categories to match the app categories exactly:")
                st.dataframe(bad[["date", "category", "amount"]].head(50), use_container_width=True, hide_index=True)
            else:
                # NOTE: Original local import append retained for reference.
                # txns_all = load_txns()
                # txns_all = pd.concat([txns_all, imp[["date", "category", "amount", "note"]]], ignore_index=True)
                # save_txns(txns_all)
                for _, row in imp.iterrows():
                    save_txn(row["date"], row["category"], row["amount"], row["note"])
                st.success(f"Imported {len(imp)} transactions.")
                st.rerun()
    except Exception as e:
        st.error(f"Could not import CSV: {e}")

st.markdown("---")

# --- Annual Spending Visual ---
st.subheader(f"6) Annual Spending — {int(year)}")

# this change was added to it on August 22 2026
st.write("DEBUG — txns rows:", len(txns))
st.write("DEBUG — txns dtypes:", txns.dtypes.astype(str).to_dict() if not txns.empty else "empty")
st.write("DEBUG — txns categories:", txns["category"].unique().tolist() if not txns.empty else "empty")
st.write("DEBUG — active_categories:", active_categories)




# Filter all transactions for the selected year
txns_year = txns.copy()
if not txns_year.empty:
    txns_year["date"] = pd.to_datetime(txns_year["date"])
    # NOTE: Annual view now respects category filter as well.
    # txns_year = txns_year[txns_year["date"].dt.year == int(year)].copy()
    txns_year = txns_year[
        (txns_year["date"].dt.year == int(year)) &
        (txns_year["category"].isin(active_categories))
    ].copy()
    txns_year["month"] = txns_year["date"].dt.month
    txns_year["month_name"] = txns_year["date"].dt.strftime("%b")

if txns_year.empty:
    st.info(f"No transactions found for {int(year)}.")
else:
    # --- Chart 1: Stacked bar — monthly total spending broken down by category ---
    monthly_cat = (
        txns_year.groupby(["month", "month_name", "category"])["amount"]
        .sum()
        .reset_index()
    )
    # Ensure months are sorted correctly
    monthly_cat = monthly_cat.sort_values("month")

    fig_stacked = px.bar(
        monthly_cat,
        x="month_name",
        y="amount",
        color="category",
        title=f"Monthly Spending by Category ({int(year)})",
        labels={"amount": "Amount ($)", "month_name": "Month", "category": "Category"},
        category_orders={"month_name": ["Jan","Feb","Mar","Apr","May","Jun",
                                         "Jul","Aug","Sep","Oct","Nov","Dec"]},
        barmode="stack",
        text_auto=False,
    )
    fig_stacked.update_layout(legend_title_text="Category", xaxis_title="Month", yaxis_title="Total Spent ($)")
    st.plotly_chart(fig_stacked, use_container_width=True)

    # --- Chart 2: Line chart — each category's spending trend month by month ---
    # Pivot so every month/category combo exists (fill 0 for missing)
    all_months = pd.DataFrame({"month": range(1, 13)})
    all_months["month_name"] = pd.to_datetime(all_months["month"], format="%m").dt.strftime("%b")

    line_data = []
    # NOTE: Build line chart only for selected categories.
    # for cat in CATEGORIES:
    for cat in active_categories:
        cat_data = monthly_cat[monthly_cat["category"] == cat][["month", "amount"]].copy()
        merged = all_months.merge(cat_data, on="month", how="left").fillna(0)
        merged["category"] = cat
        line_data.append(merged)

    line_df = pd.concat(line_data, ignore_index=True)

    fig_line = px.line(
        line_df,
        x="month_name",
        y="amount",
        color="category",
        markers=True,
        title=f"Spending Trend per Category ({int(year)})",
        labels={"amount": "Amount ($)", "month_name": "Month", "category": "Category"},
        category_orders={"month_name": ["Jan","Feb","Mar","Apr","May","Jun",
                                         "Jul","Aug","Sep","Oct","Nov","Dec"]},
    )
    fig_line.update_layout(legend_title_text="Category", xaxis_title="Month", yaxis_title="Spent ($)")
    st.plotly_chart(fig_line, use_container_width=True)

    # --- Chart 3: Heatmap — category vs month spending intensity ---
    pivot = line_df.pivot(index="category", columns="month_name", values="amount")
    month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    pivot = pivot.reindex(columns=[m for m in month_order if m in pivot.columns])

    fig_heat = px.imshow(
        pivot,
        title=f"Spending Heatmap — Category × Month ({int(year)})",
        labels={"x": "Month", "y": "Category", "color": "Amount ($)"},
        color_continuous_scale="Reds",
        aspect="auto",
        text_auto=".0f",
    )
    fig_heat.update_layout(xaxis_title="Month", yaxis_title="Category")
    st.plotly_chart(fig_heat, use_container_width=True)

    # --- Annual summary table ---
    annual_summary = (
        txns_year.groupby("category")["amount"]
        .sum()
        # NOTE: Annual summary categories follow active category filter.
        # .reindex(CATEGORIES)
        .reindex(active_categories)
        .fillna(0.0)
        .reset_index()
        .rename(columns={"amount": "total_spent"})
    )
    
    #annual_summary["avg_per_month"] = (annual_summary["total_spent"] / 12).round(2)
    #budgets_for_annual = load_budgets()
    #annual_summary = annual_summary.merge(budgets_for_annual, on="category", how="left")
    #annual_summary["annual_budget"] = annual_summary["monthly_budget"] * 12
    #annual_summary["vs_annual_budget"] = annual_summary["annual_budget"] - annual_summary["total_spent"]
    #annual_summary["status"] = annual_summary["vs_annual_budget"].apply(lambda x: "Over" if x < 0 else "OK")
    
#below code is the upadate I made on August 22 2026
    annual_summary["avg_per_month"] = (annual_summary["total_spent"] / 12).round(2)
    budgets_for_annual = load_budgets()
    annual_summary = annual_summary.merge(budgets_for_annual, on="category", how="left")
    annual_summary["annual_budget"] = annual_summary["monthly_budget"] * 12
    annual_summary["vs_annual_budget"] = annual_summary["annual_budget"] - annual_summary["total_spent"]

    # NEW: Remaining budget for the rest of the year (current month through December)
    current_month_int = int(month)
    months_left = 12 - current_month_int + 1  # inclusive of current month

    # Spent in the current month and after, per category
    spent_from_current = (
        txns_year[txns_year["month"] >= current_month_int]
        .groupby("category")["amount"].sum()
        .reindex(active_categories)
        .fillna(0.0)
        .reset_index()
        .rename(columns={"amount": "spent_from_current"})
    )
    annual_summary = annual_summary.merge(spent_from_current, on="category", how="left").fillna({"spent_from_current": 0.0})
    annual_summary["remaining_rest_of_year"] = (annual_summary["monthly_budget"] * months_left) - annual_summary["spent_from_current"]

    annual_summary["status"] = annual_summary["vs_annual_budget"].apply(lambda x: "Over" if x < 0 else "OK")







    

    st.write(f"**Annual totals for {int(year)}**")
    st.dataframe(
        annual_summary[["category", "total_spent", "avg_per_month", "annual_budget", "vs_annual_budget", "status"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "total_spent": st.column_config.NumberColumn("Total Spent", format="$%.2f"),
            "avg_per_month": st.column_config.NumberColumn("Avg/Month", format="$%.2f"),
            "annual_budget": st.column_config.NumberColumn("Annual Budget", format="$%.2f"),
            "vs_annual_budget": st.column_config.NumberColumn("Remaining vs Budget", format="$%.2f"),
        }
    )
