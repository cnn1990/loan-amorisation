import streamlit as st
import pandas as pd

st.set_page_config(page_title="Loan vs Rent Amortization", layout="wide")

# ------------------- FUNCTIONS -------------------

def calculate_emi(P, annual_rate, years):
    r = annual_rate / (12 * 100)
    n = years * 12
    emi = P * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return emi

def highlight_cashflow(row):
    if row["Cashflow Positive"]:
        return ["background-color: #d4edda"] * len(row)
    return [""] * len(row)


def generate_amortization(
    property_value,
    down_payment_percent,
    annual_interest_rate,
    tenure_years,
    base_monthly_rent,
    annual_rent_increase,
    vacancy_months
):
    down_payment = property_value * down_payment_percent / 100
    loan_amount = property_value - down_payment

    emi = calculate_emi(loan_amount, annual_interest_rate, tenure_years)
    monthly_rate = annual_interest_rate / (12 * 100)

    balance = loan_amount
    rows = []

    for month in range(1, tenure_years * 12 + 1):
        year = (month - 1) // 12

        escalated_rent = base_monthly_rent * ((1 + annual_rent_increase / 100) ** year)

        # Vacancy: last N months of each year
        if (month - 1) % 12 >= (12 - vacancy_months):
            effective_rent = 0
        else:
            effective_rent = escalated_rent

        interest = balance * monthly_rate
        principal = emi - interest
        balance -= principal

        rows.append({
            "Year": year + 1,
            "Month": month,
            "Principal Paid": round(principal, 2),
            "Interest Charged": round(interest, 2),
            "Total EMI": round(emi, 2),
            "Outstanding Balance": round(max(balance, 0), 2),
            "Rent Received": round(effective_rent, 2),
            "Amount Paid by User": round(emi - effective_rent, 2)
        })

    return pd.DataFrame(rows), emi


# ------------------- SIDEBAR INPUTS -------------------

st.sidebar.header("Loan & Rental Inputs")

property_value = st.sidebar.number_input(
    "Property Value (₹)",
    value=22_000_000,
    step=500_000
)

down_payment_percent = st.sidebar.slider(
    "Down Payment (%)",
    min_value=0,
    max_value=50,
    value=10
)

interest_rate = st.sidebar.slider(
    "Interest Rate (%)",
    min_value=5.0,
    max_value=15.0,
    value=7.4,
    step=0.1
)

tenure_years = st.sidebar.slider(
    "Loan Tenure (Years)",
    min_value=5,
    max_value=30,
    value=20
)

rent_mode = st.sidebar.radio(
    "Rent Input Mode",
    ["Monthly Rent", "Rental Yield (%)"]
)

annual_rent_increase = st.sidebar.slider(
    "Annual Rent Increase (%)",
    min_value=0.0,
    max_value=15.0,
    value=5.0,
    step=0.5
)

if rent_mode == "Monthly Rent":
    monthly_rent = st.sidebar.number_input(
        "Monthly Rent (₹)",
        value=75_000,
        step=5_000
    )
else:
    rental_yield = st.sidebar.slider(
        "Rental Yield (%)",
        min_value=1.0,
        max_value=10.0,
        value=4.0,
        step=0.1
    )
    monthly_rent = (property_value * rental_yield / 100) / 12


vacancy_months = st.sidebar.slider(
    "Vacancy (months per year)",
    min_value=0,
    max_value=3,
    value=1
)


# ------------------- CALCULATIONS -------------------

df, emi = generate_amortization(
    property_value,
    down_payment_percent,
    interest_rate,
    tenure_years,
    monthly_rent,
    annual_rent_increase,
    vacancy_months
)

# ------------------- YEAR FILTER -------------------

st.subheader("📅 Year-wise Amortization")

year_options = sorted(df["Year"].unique())
selected_year = st.selectbox("Select Year", year_options)

year_df = df[df["Year"] == selected_year]

st.dataframe(
    year_df.drop(columns=["Year"]),
    use_container_width=True
)


# ------------------- MAIN DASHBOARD -------------------
# Rent & cashflow for selected year

st.title("🏠 Loan Amortization with Rental Cash Flow")

col1, col2, col3 = st.columns(3)

year_df = df[df["Year"] == selected_year]

avg_monthly_rent_year = year_df["Rent Received"].mean()
avg_outflow_year = year_df["Amount Paid by User"].mean()

with col1:
    st.metric("Monthly EMI (Fixed)", f"₹ {emi:,.0f}")

with col2:
    st.metric(
        f"Avg Monthly Rent (Year {selected_year})",
        f"₹ {avg_monthly_rent_year:,.0f}"
    )

with col3:
    st.metric(
        f"Avg Out-of-Pocket (Year {selected_year})",
        f"₹ {avg_outflow_year:,.0f}"
    )




# ------------------- EXPORT -------------------

from io import BytesIO

# ------------------- EXPORT -------------------

st.subheader("⬇ Export Full Report")

buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="Amortization")

buffer.seek(0)

st.download_button(
    label="Download Full Amortization Report (Excel)",
    data=buffer,
    file_name="loan_rent_amortization.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# ------------------- SUMMARY -------------------

break_even_year = None

for year in df["Year"].unique():
    yearly = df[df["Year"] == year]
    if yearly["Rent Received"].mean() >= emi:
        break_even_year = year
        break

        
st.subheader("📊 Loan Summary")

total_interest = df["Interest Charged"].sum()
total_paid = df["Total EMI"].sum()

st.write(f"**Total Loan Paid:** ₹ {total_paid:,.0f}")
st.write(f"**Total Interest Paid:** ₹ {total_interest:,.0f}")
total_rent = df["Rent Received"].sum()
df["Cashflow Positive"] = df["Rent Received"] >= df["Total EMI"]

if break_even_year:
    st.success(f"✅ Break-even achieved in Year {break_even_year}")
else:
    st.warning("❌ Break-even not achieved within loan tenure")
    
st.write(f"**Total Rent Received ({tenure_years} yrs):** ₹ {total_rent:,.0f}")

starting_rent = monthly_rent
ending_year_index = tenure_years - 1

ending_rent = monthly_rent * ((1 + annual_rent_increase / 100) ** ending_year_index)

st.info(
    f"📈 Rent grows from ₹ {starting_rent:,.0f} → ₹ {ending_rent:,.0f} "
    f"over {tenure_years} years ({annual_rent_increase}% annual increase)"
)


