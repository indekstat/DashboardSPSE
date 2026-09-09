import streamlit as st
import pandas as pd
from database import get_all_jobs, init_db
from scraper import run_scraper
import threading
import time
import schedule
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

st.set_page_config(page_title="SPSE Job Opportunities", layout="wide")

# Ensure DB is initialized
init_db()

# --- Background Task Setup ---
# We use schedule to run it every hour
def start_scheduler():
    schedule.every(3).hours.do(lambda: run_scraper(limit=None)) # Adjust limit as needed, None = all
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start background thread only once
if 'scheduler_started' not in st.session_state:
    st.session_state.scheduler_started = True
    logging.info("Starting background scheduler...")
    t = threading.Thread(target=start_scheduler, daemon=True)
    t.start()

# --- Dashboard UI ---
st.title("SPSE Job Opportunities Dashboard")
st.markdown("Automatically checking `https://spse.inaproc.id` every hour for new jobs in specific categories.")

if st.button("Trigger Scraper Manually Now"):
    with st.status("Scraping in progress... this might take a while.", expanded=True) as status:
        def update_log(msg):
            status.write(msg)
            
        # Run without limit to check all sites
        run_scraper(limit=None, progress_callback=update_log)
        status.update(label="Scraping completed!", state="complete", expanded=False)
    st.success("Manual scrape completed.")
    st.rerun()

jobs = get_all_jobs()

if not jobs:
    st.info("No jobs found in the database. Try running the scraper.")
else:
    df = pd.DataFrame(jobs)
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_category = st.selectbox("Filter by Category", options=["All"] + list(df['category'].unique()))
    with col2:
        selected_source = st.selectbox("Filter by Source URL", options=["All"] + list(df['source_url'].unique()))
        
    filtered_df = df.copy()
    if selected_category != "All":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if selected_source != "All":
        filtered_df = filtered_df[filtered_df['source_url'] == selected_source]
        
    st.write(f"Showing {len(filtered_df)} jobs.")
    
    # Display as a dataframe with clickable links
    st.dataframe(
        filtered_df[['title', 'category', 'value', 'kbli', 'date_added', 'source_url', 'job_url']],
        column_config={
            "job_url": st.column_config.LinkColumn("Job Link")
        },
        hide_index=True,
        use_container_width=True
    )
