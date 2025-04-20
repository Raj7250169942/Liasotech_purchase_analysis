import streamlit as st

st.set_page_config(page_title="liasotech Purchase Analyzer", layout="wide")
import pdfplumber
import pandas as pd
import re
import plotly.express as px


# Inject Custom CSS
def local_css(css_code):
    st.markdown(f"<style>{css_code}</style>", unsafe_allow_html=True)


local_css("""
body {
    background: linear-gradient(120deg, #f6f9fc 0%, #e9eff5 100%);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.stApp {
    background-color: transparent;
}
.css-1d391kg { /* Sidebar */
    background-color: #ffffffaa;
}
.css-1dp5vir { /* Sidebar container */
    background-color: #ffffffaa;
}
.css-ffhzg2 { /* Header */
    background-color: #f8f9fa !important;
}
""")

# ---- Setup ----

st.title("📊 Liasotech Purchase Register Analyzer")

# ---- PDF Upload ----
uploaded_file = st.file_uploader("📤 Upload your purchase register PDF",
                                 type=["pdf"])

# Initialize filtered_df for fallback access
filtered_df = pd.DataFrame()

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

    def tag_category(name):
        name = name.lower()
        if "filter" in name: return "Filters"
        elif "pipe" in name: return "Pipes"
        elif "inventory" in name: return "Inventory"
        elif "valve" in name: return "Valves"
        elif "pump" in name: return "Pumps"
        else: return "Misc"

    df["Category"] = df["Item Name"].apply(tag_category)

    st.sidebar.header("🔍 Filters")

    if st.sidebar.button("🔄 Reset Filters"):
        for key in ["search", "amount", "sku", "category"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    search = st.sidebar.text_input("Search Item Name", key="search")
    amount = st.sidebar.slider("Min Amount",
                               0,
                               int(df["Amount"].max()),
                               key="amount")
    sku = st.sidebar.text_input("Filter by SKU", key="sku")
    categories = sorted(df["Category"].unique())
    selected_categories = st.sidebar.multiselect("Category",
                                                 categories,
                                                 default=categories,
                                                 key="category")

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

    st.subheader("📋 Purchase Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Amount", f"₹{filtered_df['Amount'].sum():,.2f}")
    col2.metric("Total Quantity", f"{filtered_df['Quantity'].sum():,.2f}")
    col3.metric("Unique Items", filtered_df['Item Name'].nunique())

    st.subheader("✨ Key Insights")
    try:
        most_purchased = filtered_df.loc[filtered_df["Quantity"].idxmax()]
        highest_spend = filtered_df.loc[filtered_df["Amount"].idxmax()]
        most_expensive = filtered_df.loc[filtered_df["Avg Price"].idxmax()]
    except:
        most_purchased = highest_spend = most_expensive = None

    avg_price = filtered_df["Avg Price"].mean()
    max_amount = filtered_df["Amount"].max()
    st.markdown(f"""
    - 🏆 **Most Purchased:** `{most_purchased['Item Name']}` – {most_purchased['Quantity']:.2f} units  
    - 💰 **Highest Spend:** `{highest_spend['Item Name']}` – ₹{highest_spend['Amount']:,.2f}  
    - 💎 **Most Expensive/unit:** `{most_expensive['Item Name']}` – ₹{most_expensive['Avg Price']:,.2f}  
    - 📂 **Categories:** {filtered_df["Category"].nunique()}  
    - 🔢 **Avg Unit Price:** ₹{avg_price:,.2f}  
    - 🚀 **Largest Purchase:** ₹{max_amount:,.2f}
    """)

    st.subheader("🚨 High-Value Purchases")
    high_value_df = filtered_df[filtered_df["Amount"] > 10000]
    if not high_value_df.empty:
        st.warning(f"{len(high_value_df)} purchases above ₹10,000 found.")
        st.dataframe(high_value_df)

    st.subheader("📊 Visual Insights")

    top_metric = st.selectbox("Top Items By", ["Amount", "Quantity"])
    chart_type = st.radio("Chart Type", ["Bar", "Pie"], horizontal=True)
    top_n = st.slider("Top N Items", 5, 30, 10)

    top_data = filtered_df.groupby("Item Name")[top_metric].sum().nlargest(
        top_n).reset_index()

    if chart_type == "Bar":
        fig = px.bar(top_data,
                     x="Item Name",
                     y=top_metric,
                     title=f"Top {top_n} by {top_metric}",
                     text_auto=True)
    else:
        fig = px.pie(top_data,
                     values=top_metric,
                     names="Item Name",
                     title=f"Top {top_n} by {top_metric}")

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📁 Spend by Category"):
        category_summary = filtered_df.groupby(
            "Category")["Amount"].sum().reset_index()
        fig2 = px.bar(category_summary,
                      x="Category",
                      y="Amount",
                      text_auto=True)
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("📉 Quantity vs. Unit Price"):
        fig3 = px.scatter(filtered_df,
                          x="Quantity",
                          y="Avg Price",
                          size="Amount",
                          color="Category",
                          hover_name="Item Name",
                          title="Unit Price vs Quantity")
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🔝 Top Purchases Per Category")
    cat_metric = st.selectbox("Metric", ["Amount", "Quantity"])
    per_cat_n = st.slider("Top N per Category", 3, 15, 5)

    for category in sorted(filtered_df["Category"].unique()):
        st.markdown(f"### {category}")
        sub = filtered_df[filtered_df["Category"] == category]
        top_sub = sub.groupby("Item Name")[cat_metric].sum().nlargest(
            per_cat_n).reset_index()
        fig = px.bar(top_sub, x="Item Name", y=cat_metric, text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("💸 Unusual Price Alerts")
    unusual = []
    for cat in filtered_df["Category"].unique():
        group = filtered_df[filtered_df["Category"] == cat]
        avg = group["Avg Price"].mean()
        flagged = group[group["Avg Price"] > avg * 1.5]
        unusual.append(flagged)
    outlier_df = pd.concat(unusual)
    if not outlier_df.empty:
        st.warning(f"{len(outlier_df)} unusually priced items found.")
        st.dataframe(outlier_df)

    st.subheader("📦 Bulk Order Detector")
    bulk_df = filtered_df[(filtered_df["Quantity"] > 500)
                          & (filtered_df["Avg Price"] < 100)]
    if not bulk_df.empty:
        st.info(f"{len(bulk_df)} bulk orders found.")
        st.dataframe(bulk_df)
    else:
        st.success("No bulk orders detected.")

    with st.expander("📊 Advanced Category Summary"):
        col1, col2 = st.columns(2)
        avg_by_cat = filtered_df.groupby(
            "Category")["Avg Price"].mean().reset_index()
        qty_by_cat = filtered_df.groupby(
            "Category")["Quantity"].sum().reset_index()

        fig1 = px.bar(avg_by_cat,
                      x="Category",
                      y="Avg Price",
                      text_auto=True,
                      title="Avg Price per Category")
        fig2 = px.bar(qty_by_cat,
                      x="Category",
                      y="Quantity",
                      text_auto=True,
                      title="Total Quantity per Category")

        col1.plotly_chart(fig1, use_container_width=True)
        col2.plotly_chart(fig2, use_container_width=True)

# ---- AI-Powered Analysis ----
with st.expander("🤖 Ask AI About This Data", expanded=True):
    st.markdown(
        "Try asking things like: `Which category had the highest average price?` or `Top 5 expensive items?`"
    )
    if filtered_df.empty:
        st.info("📄 Upload a PDF and apply filters to enable chat.")
    question = st.text_input("💬 Ask a question")

    def smart_fallback(question):
        q = question.lower()

        def _safe_idxmax(col):
            return filtered_df.loc[
                filtered_df[col].idxmax()] if not filtered_df.empty else None

        if any(x in q for x in
               ["highest average price", "avg price", "costliest category"]):
            result = filtered_df.groupby(
                "Category")["Avg Price"].mean().idxmax()
            return f"📈 The category with the highest average unit price is **{result}**."

        elif any(x in q for x in
                 ["most purchased", "highest quantity", "max quantity"]):
            row = _safe_idxmax("Quantity")
            return f"🏆 Most purchased item is **{row['Item Name']}** with **{row['Quantity']} units**." if row is not None else "No data available."

        elif any(x in q for x in ["most expensive", "highest unit price"]):
            row = _safe_idxmax("Avg Price")
            return f"💎 Most expensive item is **{row['Item Name']}** at ₹{row['Avg Price']:.2f} per unit." if row is not None else "No data available."

        elif any(x in q
                 for x in ["highest spend", "most spent", "biggest purchase"]):
            row = _safe_idxmax("Amount")
            return f"💰 Highest spend was on **{row['Item Name']}** totaling ₹{row['Amount']:,.2f}." if row is not None else "No data available."

        elif "top" in q and "items" in q:
            match = re.search(r"top (\d+)", q)
            n = int(match.group(1)) if match else 5
            by = "Amount" if "amount" in q or "spend" in q else "Quantity" if "quantity" in q else "Amount"
            top_items = filtered_df.groupby("Item Name")[by].sum().nlargest(
                n).reset_index()
            return f"📋 Top {n} items by {by.lower()}:\n" + "\n".join([
                f"- {row['Item Name']} – ₹{row[by]:,.2f}" if by == "Amount"
                else f"- {row['Item Name']} – {row[by]} units"
                for _, row in top_items.iterrows()
            ])

        elif "average price per category" in q:
            result = filtered_df.groupby(
                "Category")["Avg Price"].mean().reset_index()
            return "📊 Average price per category:\n" + "\n".join([
                f"- {r['Category']}: ₹{r['Avg Price']:.2f}"
                for _, r in result.iterrows()
            ])

        else:
            return "🤖 Sorry, I can only answer basic data questions without external AI."

    if question:
        if filtered_df.empty:
            st.warning(
                "⚠️ Please upload and process a PDF before using the chatbot.")
        else:
            with st.spinner("Analyzing..."):
                try:
                    if "OPENAI_API_KEY" in st.secrets and st.secrets[
                            "OPENAI_API_KEY"]:
                        from openai import OpenAI
                        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

                        csv_data = filtered_df.to_csv(index=False)
                        prompt = f"""You're a purchase data assistant. Based on this CSV data:\n\n{csv_data}\n\nAnswer this user question: {question}"""

                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{
                                "role":
                                "system",
                                "content":
                                "You're a helpful assistant for analyzing purchase data."
                            }, {
                                "role": "user",
                                "content": prompt
                            }],
                            temperature=0.4,
                            max_tokens=500)
                        st.success("✅ AI Response:")
                        st.markdown(response.choices[0].message.content)

                    else:
                        st.warning(
                            "⚠️ No OpenAI API key detected. Using local logic..."
                        )
                        st.markdown(smart_fallback(question))

                except Exception as e:
                    st.warning(
                        "⚠️ AI not available or quota exceeded. Using local logic..."
                    )
                    st.markdown(smart_fallback(question))
