#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
import re


# In[ ]:


# --- Data Preparation ---
@st.cache_data
def load_and_prepare_data(file_path):
    """
    Loads financial data, cleans it, converts types, and calculates growth metrics.
    Caches the result to avoid re-running on every Streamlit interaction.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please ensure it's in the same directory as the app.")
        return pd.DataFrame() # Return an empty DataFrame on error

# Data Cleaning and Type Conversion 
# List of columns that should be numeric
numeric_cols = [
    'Total Revenue ($M)',
    'Net Income ($M)',
    'Total Assets ($M)',
    'Total Liabilities ($M)',
    'Cash Flow from Operating Activities ($M)'
]

# Apply cleaning and conversion to each numeric column
for col in numeric_cols:
    if col in df.columns: # Check if the column exists
        # Convert to string, remove commas, remove any leading/trailing spaces, then convert to numeric
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce')
    else:
        print(f"Warning: Column '{col}' not found in DataFrame. Please check your CSV header names.")

# Sort data before calculating percentage change 
# Ensure 'Fiscal Year' is sorted correctly for pct_change to work across years within each company
df = df.sort_values(by=['Company', 'Fiscal Year'])

# Calculate year-over-year changes 
df['Revenue Growth (%)'] = df.groupby('Company')['Total Revenue ($M)'].pct_change() * 100
df['Net Income Growth (%)'] = df.groupby('Company')['Net Income ($M)'].pct_change() * 100
df['Total Assets Growth (%)'] = df.groupby('Company')['Total Assets ($M)'].pct_change() * 100
df['Total Liabilities Growth (%)'] = df.groupby('Company')['Total Liabilities ($M)'].pct_change() * 100
df['Cash Flow from Operating Activities Growth (%)'] = df.groupby('Company')['Cash Flow from Operating Activities ($M)'].pct_change() * 100

# Fill NA values that result from pct_change calculations with 0 or an appropriate value
df.fillna(0, inplace=True)
return df


# In[ ]:


# --- Chatbot Logic ---
def get_financial_insight(query, financial_df):
    """
    Processes a user query about financial data using rule-based logic and adds
    interactive suggestions for follow-up questions.
    """
    query = query.lower() # Convert query to lowercase for case-insensitive matching

    # --- 1. Identify Company ---
    # The assistant first tries to figure out which company you're asking about.
    company = None # Starts by assuming no company is identified yet.
    if "microsoft" in query:
        company = "Microsoft"
    elif "tesla" in query:
        company = "Tesla"
    elif "apple" in query:
        company = "Apple"

    if not company:
        return "I need a company name (Microsoft, Tesla, or Apple) to provide financial insights. Please try again."

    # Now that it knows the company, it goes to your big data table ('financial_df')
    # and pulls out *only* the rows that belong to that specific company.
    company_data = financial_df[financial_df['Company'] == company]
    if company_data.empty:
        return f"No data available for **{company}**. Please check the company name or the dataset."


    # --- 2. Identify Specific Year in Query ---
    requested_year = None
    # This line uses a regular expression (re) to look for a four-digit number
    # that matches the years 2022, 2023, or 2024 within your question.
    # '\b' ensures it matches whole words (e.g., '2022' not just part of 'something2022').
    year_match = re.search(r'\b(202[2-4])\b', query) # Pattern specifically for 2022, 2023, 2024
    if year_match:
        # If a year is found, it converts it to a number.
        requested_year = int(year_match.group(1))

    # --- 3. Select Data for the Requested Year or Latest Year ---
    selected_year_data = None
    actual_year_used = None # This variable will store the year that the chatbot actually uses for its response.

    # Initialise response_parts here to ensure it always exists
    response_parts = []
    
    # If a specific year was asked for AND that year exists for the company in the data:
    if requested_year and requested_year in company_data['Fiscal Year'].values:
        # It picks the row that matches the exact requested year.
        selected_year_data = company_data[company_data['Fiscal Year'] == requested_year].iloc[0]
        actual_year_used = requested_year # The year used is the requested year.
    else:
        # If no year was asked for, or the requested year isn't in the data for that company,
        # it defaults to using the data from the latest available year (.iloc[-1]).
        selected_year_data = company_data.iloc[-1]
        actual_year_used = selected_year_data['Fiscal Year'] # The year used is the latest year.
        
        # If a year was requested but not found, it adds a polite message to the response.
        if requested_year:
            response_parts = [f"I couldn't find data for {company} in FY{requested_year}. Displaying data for FY{actual_year_used} instead. "]
        else:
            # If no specific year was requested, start with an empty list for response parts.
            response_parts = []

    # Use selected_year_data instead of latest_year_data for all metric lookups from now on.
    response_parts_temp = [] # A temporary list to build the main part of the response.
    metric_found = False # A flag to track if any specific metric was found in the query.
    
    # --- 4. Identify Metric and Construct Response ---
    # This section checks what specific financial number or growth rate you're asking for.

    # Check for absolute financial numbers (like total revenue, net income, etc.)
    if "total revenue" in query or "revenue" in query:
        value = selected_year_data['Total Revenue ($M)']
        response_parts_temp.append(f"{company}'s Total Revenue for FY{actual_year_used} was ${value:,.0f}M.")
        metric_found = True
    if "net income" in query or "profit" in query:
        value = selected_year_data['Net Income ($M)']
        response_parts_temp.append(f"{company}'s Net Income for FY{actual_year_used} was ${value:,.0f}M.")
        metric_found = True
    if "total assets" in query or "assets" in query:
        value = selected_year_data['Total Assets ($M)']
        response_parts_temp.append(f"{company}'s Total Assets for FY{actual_year_used} were ${value:,.0f}M.")
        metric_found = True
    if "total liabilities" in query or "liabilities" in query:
        value = selected_year_data['Total Liabilities ($M)']
        response_parts_temp.append(f"{company}'s Total Liabilities for FY{actual_year_used} were ${value:,.0f}M.")
        metric_found = True
    if "cash flow from operating activities" in query or "operating cash flow" in query or "cash flow" in query:
        value = selected_year_data['Cash Flow from Operating Activities ($M)']
        response_parts_temp.append(f"{company}'s Cash Flow from Operating Activities for FY{actual_year_used} was ${value:,.0f}M.")
        metric_found = True

    # Check for growth rates.
    # Growth percentages are always relative to the previous year available.
    # In our data, 2022 won't have growth, as there's no 2021 in the dataset.
    if len(company_data) > 1: # Only try to get growth if there's enough data for it.
        if "revenue growth" in query:
            value = selected_year_data['Revenue Growth (%)']
            # If the growth value is missing (NaN), it means there's no prior year to calculate from.
            if pd.isna(value):
                response_parts_temp.append(f"{company}'s Revenue Growth data for FY{actual_year_used} is not available (requires previous year's data).")
            else:
                response_parts_temp.append(f"{company}'s Revenue Growth for FY{actual_year_used} was {value:.2f}%.")
            metric_found = True
        if "net income growth" in query or "profit growth" in query:
            value = selected_year_data['Net Income Growth (%)']
            if pd.isna(value):
                 response_parts_temp.append(f"{company}'s Net Income Growth data for FY{actual_year_used} is not available (requires previous year's data).")
            else:
                response_parts_temp.append(f"{company}'s Net Income Growth for FY{actual_year_used} was {value:.2f}%.")
            metric_found = True
        if "assets growth" in query:
            value = selected_year_data['Total Assets Growth (%)']
            if pd.isna(value):
                response_parts_temp.append(f"{company}'s Total Assets Growth data for FY{actual_year_used} is not available (requires previous year's data).")
            else:
                response_parts_temp.append(f"{company}'s Total Assets Growth for FY{actual_year_used} was {value:.2f}%.")
            metric_found = True
        if "liabilities growth" in query:
            value = selected_year_data['Total Liabilities Growth (%)']
            if pd.isna(value):
                response_parts_temp.append(f"{company}'s Total Liabilities Growth data for FY{actual_year_used} is not available (requires previous year's data).")
            else:
                response_parts_temp.append(f"{company}'s Total Liabilities Growth for FY{actual_year_used} was {value:.2f}%.")
            metric_found = True
        if "operating cash flow growth" in query or "cash flow growth" in query:
            value = selected_year_data['Cash Flow from Operating Activities Growth (%)']
            if pd.isna(value):
                response_parts_temp.append(f"{company}'s Cash Flow from Operating Activities Growth data for FY{actual_year_used} is not available (requires previous year's data).")
            else:
                response_parts_temp.append(f"{company}'s Cash Flow from Operating Activities Growth for FY{actual_year_used} was {value:.2f}%.")
            metric_found = True

    # --- 5. Handle General Summaries or Unrecognised Queries & Add Interactivity ---

    # If you asked for a summary, performance, or overview.
    if "summarise" in query or "performance" in query or "overview" in query or "financial health" in query:
        # It creates a detailed summary response with several key financial points for the actual year used.
        summary_response = f"Here's a summary of {company}'s financial performance for FY{actual_year_used}:\n"
        summary_response += f"- Total Revenue: ${selected_year_data['Total Revenue ($M)']:,}M\n"
        summary_response += f"- Net Income: ${selected_year_data['Net Income ($M)']:,}M\n"
        summary_response += f"- Cash Flow from Operations: ${selected_year_data['Cash Flow from Operating Activities ($M)']:,}M\n"
        
        # It adds growth rates to the summary if they are available for the specific year.
        # Growth is only available from 2023 onwards in your dataset, as 2022 is the first year.
        if actual_year_used in [2023, 2024] and len(company_data) > 1:
            summary_response += f"- Revenue Growth (YoY): {selected_year_data.get('Revenue Growth (%)', 'N/A'):.2f}%\n"
            summary_response += f"- Net Income Growth (YoY): {selected_year_data.get('Net Income Growth (%)', 'N/A'):.2f}%\n"
        else:
             summary_response += f"Growth data for FY{actual_year_used} is not available (requires previous year's data in the dataset).\n"

        # After giving a summary, it suggests diving deeper or comparing years.
        summary_response += f"\nIs there a specific metric you'd like to dive deeper into, or perhaps compare another year's performance?"
        return summary_response

    # Combine any initial messages (like "year not found") with the metric-specific responses.
    response_parts.extend(response_parts_temp)

    # If specific metrics were found in the query.
    if response_parts:
        final_response = " ".join(response_parts)
        # It adds a follow-up question related to what you just asked.
        if "revenue" in query and "growth" not in query:
            final_response += f"\nWould you also like to know about {company}'s net income or revenue growth for FY{actual_year_used}?"
        elif "net income" in query and "growth" not in query:
            final_response += f"\nPerhaps {company}'s cash flow or net income growth for FY{actual_year_used} next?"
        elif "assets" in query or "liabilities" in query:
            final_response += f"\nWould you like a summary of {company}'s overall financial health for FY{actual_year_used}?"
        elif "growth" in query: # If any growth metric was asked
             final_response += f"\nWould you like to know about {company}'s other growth metrics or a summary of its financial health for FY{actual_year_used}?"
        return final_response
    else:
        # If the assistant couldn't find any specific metric or a summary request,
        # it gives you a polite message asking you to try rephrasing,
        # and reminds you what it can answer, including specific years.
        return (f"I'm not sure how to answer that about {company}. "
                f"I can tell you about its total revenue, net income, assets, liabilities, cash flow, or their growth rates. "
                f"Try asking 'What is Microsoft's revenue for 2023?' or 'Summarise Apple's performance for 2022'.")


# In[ ]:


# --- Streamlit App Layout ---
st.set_page_config(page_title="Financial Insights Chatbot", layout="centered")

st.title("💰 Financial Insights Chatbot")

st.write(
    """
    Hello! I'm here to help you understand financial data for **Microsoft, Tesla, and Apple**.
    You can ask about their **Total Revenue, Net Income, Total Assets, Total Liabilities, Cash Flow from Operating Activities**, or their **growth rates**.
    You can also ask for specific years between **2022 and 2024**.
    """
)

st.info("💡 **Examples:**\n"
        "- `What is Apple's revenue for 2022?`\n"
        "- `Tell me about Microsoft's net income growth.`\n"
        "- `Summarise Tesla's performance for 2023.`")

# Load data only once and cache it for efficiency
df = load_and_prepare_data('financial_data.csv')

if not df.empty:
    # Initialize chat history in session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    user_query = st.chat_input("Your query:")

    if user_query:
        # Add user message to chat history and display
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Get chatbot response
        chatbot_response = get_financial_insight(user_query, df)

        # Add chatbot response to chat history and display
        st.session_state.messages.append({"role": "assistant", "content": chatbot_response})
        with st.chat_message("assistant"):
            st.markdown(chatbot_response)

    st.markdown("---")
    st.write("Feel free to ask another question or close the tab to end the session.")
else:
    st.warning("Please ensure 'financial_data.csv' is correctly placed and contains valid data for the chatbot to function.")


# In[ ]:




