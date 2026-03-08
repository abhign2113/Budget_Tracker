import os
import pandas as pd
import streamlit as st
from datetime import date
import plotly.express as px


st.set_page_config(page_title="Budget Tracker", layout="wide")

# --- Password Protection ---
PASSWORD = "1991"  # Change this to your own password

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

BUDGET_FILE = "budgets.csv"
TXN_FILE = "transactions.csv"
SETTINGS_FILE = "settings.csv"  # stores monthly income
EXTRA_INCOME_FILE = "extra_income.csv"


def load_budgets() -> pd.DataFrame:
    if os.path.exists(BUDGET_FILE):
        df = pd.read_csv(BUDGET_FILE)
        existing = set(df["category"].tolist())
        missing = [c for c in CATEGORIES if c not in existing]
        if missing:
            df = pd.concat(
                [df, pd.DataFrame({"category": missing, "monthly_budget": [0.0] * len(missing)})],
                ignore_index=True,
            )
        return df[["category", "monthly_budget"]].sort_values("category").reset_index(drop=True)
    return pd.DataFrame({"category": CATEGORIES, "monthly_budget": [0.0] * len(CATEGORIES)})


def save_budgets(df: pd.DataFrame) -> None:
    df.to_csv(BUDGET_FILE, index=False)


def load_txns() -> pd.DataFrame:
    if os.path.exists(TXN_FILE):
        df = pd.read_csv(TXN_FILE)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df
    return pd.DataFrame(columns=["date", "category", "amount", "note"])


def save_txns(df: pd.DataFrame) -> None:
    df.to_csv(TXN_FILE, index=False)


def month_filter(df: pd.DataFrame, y: int, m: int) -> pd.DataFrame:
    if df.empty:
        return df
    d = pd.to_datetime(df["date"])
    return df[(d.dt.year == y) & (d.dt.month == m)].copy()


def load_income() -> float:
    if os.path.exists(SETTINGS_FILE):
        s = pd.read_csv(SETTINGS_FILE)
        if "monthly_income" in s.columns and len(s) > 0:
            try:
                return float(s.loc[0, "monthly_income"])
            except Exception:
                return 0.0
    return 0.0


def save_income(value: float) -> None:
    pd.DataFrame([{"monthly_income": float(value)}]).to_csv(SETTINGS_FILE, index=False)

def load_extra_income(y, m):
    if os.path.exists(EXTRA_INCOME_FILE):
        df = pd.read_csv(EXTRA_INCOME_FILE)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        d = pd.to_datetime(df["date"])
        return df[(d.dt.year == y) & (d.dt.month == m)]
    return pd.DataFrame(columns=["date", "description", "amount"])



def save_extra_income(df):
    if os.path.exists(EXTRA_INCOME_FILE):
        existing = pd.read_csv(EXTRA_INCOME_FILE)
        existing["date"] = pd.to_datetime(existing["date"]).dt.date
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df
    combined.to_csv(EXTRA_INCOME_FILE, index=False)


st.title("💸 Personal Budget Tracker")

# --- Sidebar: month selection ---
today = date.today()
colA, colB = st.sidebar.columns(2)
year = colA.number_input("Year", min_value=2000, max_value=2100, value=today.year, step=1)
month = colB.number_input("Month", min_value=1, max_value=12, value=today.month, step=1)

st.sidebar.markdown("---")
st.sidebar.caption("Data is stored locally in budgets.csv, transactions.csv, settings.csv")


# --- Income ---
st.subheader("0) Set monthly income (salary)")
current_income = load_income()
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

st.subheader("0b) Log extra income (sales, bonus, etc.)")
with st.form("extra_income_form", clear_on_submit=True):
    ei_col1, ei_col2, ei_col3 = st.columns(3)
    ei_date = ei_col1.date_input("Date", value=today, key="ei_date")
    ei_desc = ei_col2.text_input("Description (e.g. Sold TV)")
    ei_amt = ei_col3.number_input("Amount", min_value=0.0, step=1.0, format="%.2f", key="ei_amt")
    ei_submitted = st.form_submit_button("Add Extra Income")
    
# Show extra income entries for the month with delete option
extra_income_m = load_extra_income(int(year), int(month))
if not extra_income_m.empty:
    st.write("Extra income this month:")
    extra_income_m = extra_income_m.reset_index()
    for i, row in extra_income_m.iterrows():
        col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
        col1.write(row["date"])
        col2.write(row["description"])
        col3.write(f"${row['amount']:.2f}")
        if col4.button("Delete", key=f"ei_del_{i}"):
            all_ei = pd.read_csv(EXTRA_INCOME_FILE)
            all_ei = all_ei.drop(row["index"])
            all_ei.to_csv(EXTRA_INCOME_FILE, index=False)
            st.rerun()

if ei_submitted:
    if ei_amt <= 0:
        st.error("Amount must be greater than 0.")
    else:
        new_ei = pd.DataFrame([{"date": ei_date, "description": ei_desc, "amount": float(ei_amt)}])
        save_extra_income(new_ei)
        st.success(f"Extra income of ${ei_amt:.2f} added!")

        


# --- Load data ---
budgets = load_budgets()
txns = load_txns()
txns_m = month_filter(txns, int(year), int(month))

# --- Budgets editor ---
st.subheader("1) Set monthly budgets")
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
st.subheader("2) Add a transaction")
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
        new_row = pd.DataFrame([{"date": txn_date, "category": cat, "amount": float(amt), "note": note}])
        txns = pd.concat([txns, new_row], ignore_index=True)
        save_txns(txns)
        st.success("Transaction added!")


# reload month view after add
txns = load_txns()
txns_m = month_filter(txns, int(year), int(month))

st.markdown("---")


# --- Summary ---
st.subheader(f"3) Summary for {int(year)}-{int(month):02d}")

spent = (
    txns_m.groupby("category")["amount"].sum()
    .reindex(CATEGORIES)
    .fillna(0.0)
    .reset_index()
    .rename(columns={"amount": "spent"})
)

budgets_latest = load_budgets().set_index("category").reindex(CATEGORIES).fillna(0.0).reset_index()
summary = budgets_latest.merge(spent, on="category", how="left").fillna({"spent": 0.0})
summary["remaining_in_category"] = summary["monthly_budget"] - summary["spent"]
summary["status"] = summary["remaining_in_category"].apply(lambda x: "Over" if x < 0 else "OK")


# Totals
total_budget = float(summary["monthly_budget"].sum())
total_spent = float(summary["spent"].sum())


# Income-based rollups
income = float(load_income())
extra_income_m = load_extra_income(int(year), int(month))
total_extra_income = float(extra_income_m["amount"].sum()) if not extra_income_m.empty else 0.0
total_available = income + total_extra_income
remaining_after_spend = total_available - total_spent
planned_remaining_after_budget = total_available - total_budget
over_under_budget_vs_spend = total_budget - total_spent

summary["savings_in_category"] = summary.apply(
    lambda row: max(row["monthly_budget"] - row["spent"], 0.0), axis=1
)
savings_from_budget = float(summary["savings_in_category"].sum())
total_projected_remaining = planned_remaining_after_budget + savings_from_budget

k1, k2, k3, k4 = st.columns(4)
k1.metric("Monthly Income", f"${income:,.2f}")
k2.metric("Total Budget (Planned)", f"${total_budget:,.2f}")
k3.metric("Total Spent (Actual)", f"${total_spent:,.2f}")
k4.metric("Remaining After Spending", f"${remaining_after_spend:,.2f}")

k5, k6, k7, k8 = st.columns(4)
k5.metric("Planned Remaining After Budget", f"${planned_remaining_after_budget:,.2f}")
k6.metric("Under/Over Budget (Budget - Spent)", f"${over_under_budget_vs_spend:,.2f}")
k7.metric("Savings From This Month's Budget", f"${savings_from_budget:,.2f}")
k8.metric("Projected Total Remaining", f"${total_projected_remaining:,.2f}")

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
st.subheader("4) Transactions (this month)")

if txns_m.empty:
    st.info("No transactions recorded for this month yet.")
else:
    txns_m = txns_m.reset_index()
    for i, row in txns_m.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 1])
        col1.write(row["date"])
        col2.write(row["category"])
        col3.write(f"${row['amount']}")
        col4.write(row["note"])
        if col5.button("Delete", key=i):
            txns_all = load_txns()
            txns_all = txns_all.drop(row["index"])
            save_txns(txns_all)
            st.rerun()

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
                txns_all = load_txns()
                txns_all = pd.concat([txns_all, imp[["date", "category", "amount", "note"]]], ignore_index=True)
                save_txns(txns_all)
                st.success(f"Imported {len(imp)} transactions.")
    except Exception as e:
        st.error(f"Could not import CSV: {e}")

st.markdown("---")

# --- Annual Spending Visual ---
st.subheader(f"6) Annual Spending — {int(year)}")

# Filter all transactions for the selected year
txns_year = txns.copy()
if not txns_year.empty:
    txns_year["date"] = pd.to_datetime(txns_year["date"])
    txns_year = txns_year[txns_year["date"].dt.year == int(year)].copy()
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
    for cat in CATEGORIES:
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
        .reindex(CATEGORIES)
        .fillna(0.0)
        .reset_index()
        .rename(columns={"amount": "total_spent"})
    )
    annual_summary["avg_per_month"] = (annual_summary["total_spent"] / 12).round(2)
    budgets_for_annual = load_budgets()
    annual_summary = annual_summary.merge(budgets_for_annual, on="category", how="left")
    annual_summary["annual_budget"] = annual_summary["monthly_budget"] * 12
    annual_summary["vs_annual_budget"] = annual_summary["annual_budget"] - annual_summary["total_spent"]
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
