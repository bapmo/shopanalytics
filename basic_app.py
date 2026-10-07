import sqlite3
import pandas as pd
import streamlit as st

conn = sqlite3.connect("shop.db")

st.title("Shop Analytics")

st.subheader("Revenue by category")
df = pd.read_sql_query("""
    SELECT p.category, SUM(oi.quantity * p.price) AS revenue
    FROM order_items oi JOIN products p ON p.product_id = oi.product_id
    GROUP BY p.category
""", conn)
st.bar_chart(df, x="category", y="revenue")

st.subheader("Run your own SQL")
sql = st.text_area("Query", "SELECT * FROM customers;")
if st.button("Run"):
    try:
        st.dataframe(pd.read_sql_query(sql, conn))
    except Exception as e:
        st.error(e)