import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px

# ----- Page Setup -----
st.set_page_config(page_title="Liasotech Purchase Analyzer", layout="wide")
st.title("📊 Liasotech Purchase Item Analysis")

# ----- Upload PDF -----
uploaded_file = st.file_uploader("📤 Upload your purchase register PDF",
                                 type=["pdf"])

# ----- Data Extraction -----
if uploaded_file:
    data = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    match = re.match(
                        r"^(.*?)\s+([\d,\.]+)\s+₹([\d,\.]+)\s+₹([\d,\.]+)(?:\s+(.*))?$",
                        line)
                    if match:
                        item_name = match.group(1).strip()
                        qty = float(match.group(2).replace(",", ""))
                        amount = float(match.group(3).replace(",", ""))
                        avg_price = float(match.group(4).replace(",", ""))
                        sku = match.group(5).strip() if match.group(5) else ""
                        data.append([item_name, qty, amount, avg_price, sku])

    df = pd.DataFrame(
        data, columns=["Item Name", "Quantity", "Amount", "Avg Price", "SKU"])

    # ----- Auto-Tag Categories -----
    def tag_category(name):
        name = name.lower()
        if "filter" in name:
            return "Filters"
        elif "pipe" in name:
            return "Pipes"
        elif "inventory" in name:
            return "Inventory"
        elif "valve" in name:
            return "Valves"
        elif "pump" in name:
            return "Pumps"
        else:
            return "Misc"

    df["Category"] = df["Item Name"].apply(tag_category)

    # ----- Sidebar Filters -----
    st.sidebar.header("🔍 Filters")

    if st.sidebar.button("🔄 Reset Filters"):
        for key in ["search", "amount", "sku", "category"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    search = st.sidebar.text_input("🔎 Search Item Name", key="search")
    amount = st.sidebar.slider("🪙 Min Amount",
                               0,
                               int(df["Amount"].max()),
                               key="amount")
    sku = st.sidebar.text_input("🔎 Filter by SKU", key="sku")
    category_options = sorted(df["Category"].unique())
    selected_categories = st.sidebar.multiselect("📁 Filter by Category",
                                                 category_options,
                                                 default=category_options,
                                                 key="category")

    # ----- Apply Filters -----
    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df["Item Name"].str.contains(
            search, case=False)]
    if amount > 0:
        filtered_df = filtered_df[filtered_df["Amount"] >= amount]
    if sku:
        filtered_df = filtered_df[filtered_df["SKU"].str.contains(sku,
                                                                  case=False)]
    if selected_categories:
        filtered_df = filtered_df[filtered_df["Category"].isin(
            selected_categories)]

    # ----- KPIs -----
    st.markdown("### 📋 Purchase Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("🧾 Total Amount", f"₹{filtered_df['Amount'].sum():,.2f}")
    col2.metric("📦 Total Quantity", f"{filtered_df['Quantity'].sum():,.2f}")
    col3.metric("🔢 Unique Items", filtered_df["Item Name"].nunique())

    # ----- Key Insights -----
    st.markdown("### ✨ Key Insights")

    most_purchased = filtered_df.loc[filtered_df["Quantity"].idxmax()]
    highest_spend = filtered_df.loc[filtered_df["Amount"].idxmax()]
    most_expensive_unit = filtered_df.loc[filtered_df["Avg Price"].idxmax()]
    avg_unit_cost = filtered_df["Avg Price"].mean()
    max_single_purchase = filtered_df["Amount"].max()
    total_categories = filtered_df["Category"].nunique()

    st.markdown(f"""
    - 🏆 **Most Purchased Item (Qty):** `{most_purchased['Item Name']}` – {most_purchased['Quantity']:.2f} units  
    - 💸 **Highest Spend Item:** `{highest_spend['Item Name']}` – ₹{highest_spend['Amount']:,.2f}  
    - 🧨 **Most Expensive per Unit:** `{most_expensive_unit['Item Name']}` – ₹{most_expensive_unit['Avg Price']:,.2f}/unit  
    - 🗂️ **Total Categories:** {total_categories}  
    - 🧮 **Average Unit Cost:** ₹{avg_unit_cost:,.2f}  
    - 💰 **Largest Single Purchase:** ₹{max_single_purchase:,.2f}
    """)

    # ----- Flag High-Value Purchases -----
    high_value_threshold = 10000
    high_value_items = filtered_df[filtered_df["Amount"] >
                                   high_value_threshold]

    if not high_value_items.empty:
        st.warning(
            f"🚨 {len(high_value_items)} High-Value Purchases Over ₹{high_value_threshold:,} Found"
        )
        with st.expander("🔍 View High-Value Items"):
            st.dataframe(high_value_items)

    # ----- Chart Controls -----
    st.markdown("## 📊 Visual Insights")
    chart_column = st.selectbox("📌 View Top Items by:", ["Amount", "Quantity"])
    chart_type = st.radio("📈 Chart Type", ["Bar Chart", "Pie Chart"],
                          horizontal=True)
    top_n = st.slider("🔢 Number of Top Items",
                      min_value=5,
                      max_value=30,
                      value=10)

    top_data = (filtered_df.groupby("Item Name")[chart_column].sum().nlargest(
        top_n).reset_index())

    if chart_type == "Bar Chart":
        fig = px.bar(top_data,
                     x="Item Name",
                     y=chart_column,
                     title=f"Top {top_n} by {chart_column}",
                     text_auto=True)
    else:
        fig = px.pie(top_data,
                     values=chart_column,
                     names="Item Name",
                     title=f"Top {top_n} by {chart_column}")

    st.plotly_chart(fig, use_container_width=True)

    # ----- Purchase Summary by Category -----
    with st.expander("📊 Total Spend by Category"):
        category_summary = filtered_df.groupby(
            "Category")["Amount"].sum().reset_index()
        fig2 = px.bar(category_summary,
                      x="Category",
                      y="Amount",
                      title="Spend by Category",
                      text_auto=True)
        st.plotly_chart(fig2, use_container_width=True)

    # ----- Unit Price vs Quantity Scatter -----
    with st.expander("📉 Quantity vs. Unit Price"):
        fig3 = px.scatter(filtered_df,
                          x="Quantity",
                          y="Avg Price",
                          size="Amount",
                          color="Category",
                          hover_name="Item Name",
                          title="Unit Price vs. Quantity")
        st.plotly_chart(fig3, use_container_width=True)

    # ----- Data Table -----
    st.markdown("### 📄 Full Item Table")
    st.dataframe(filtered_df)

    # ----- CSV Download -----
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV",
                       data=csv,
                       file_name="purchase_data.csv",
                       mime="text/csv")

else:
    st.info("📄 Upload a PDF file to begin analysis.")
