# app.py
"""Main Streamlit app for Coral Data Toolkit"""

import streamlit as st
import numpy as np
from experiment_planner import generate_pdf, calculate_next_ramp
from form_digitizer import process_form_image
from datetime import datetime, timedelta


# ==============================================================================
# === STREAMLIT UI =============================================================
# ==============================================================================

# Sidebar with navigation buttons
st.sidebar.title("🪸 Coral Data Toolkit")
st.sidebar.markdown("---")

# Navigation buttons in sidebar
if st.sidebar.button("📖 Instructions", use_container_width=True):
    st.session_state.page = "Instructions"

if st.sidebar.button("🧪 Experiment Planner", use_container_width=True):
    st.session_state.page = "Experiment Planner"

if st.sidebar.button("📷 Datasheet Upload", use_container_width=True):
    st.session_state.page = "Datasheet Upload"

# Initialize page if not set
if 'page' not in st.session_state:
    st.session_state.page = "Instructions"

# ==============================================================================
# === PAGE 0: INSTRUCTIONS =====================================================
# ==============================================================================

if st.session_state.page == "Instructions":
    # Load and display instructions from markdown file
    try:
        with open('instructions.md', 'r') as f:
            instructions_content = f.read()
        st.markdown(instructions_content)
    except FileNotFoundError:
        st.error("Instructions file not found. Please ensure 'instructions.md' is in the same directory as the app.")

# ==============================================================================
# === PAGE 1: EXPERIMENT PLANNER ===============================================
# ==============================================================================

elif st.session_state.page == "Experiment Planner":
    st.title("🧪 Experiment Planner")
    st.write("Set up your experiment and generate the baseline (Day 0) data collection sheet.")

    # Experiment metadata (with character limit for QR code)
    exp_name = st.text_input(
        "Experiment Name", 
        "My Experiment",
        max_chars=20,
        help="Choose a name for the experiment (20 character max)"
    )
    
    start_date = st.date_input("Start Date")
    
    # Baseline temperature (required)
    baseline_temp = st.number_input(
        "Baseline Temperature (°C)", 
        min_value=25.0, 
        max_value=40.0, 
        value=29.0,
        step=0.5,
        help="Enter the baseline (control) temperature for the experiment"
    )

    # First ramp peak temperature (required)
    peak_1_temp = st.number_input(
        "First Ramp Temperature (°C)", 
        min_value=25.0, 
        max_value=40.0, 
        value=32.0,
        step=0.5,
        help="Enter the peak temperature of the first heat ramp"
    )

    # Coral ID input (usually 24 IDs for 6x4 grid)
    st.write("**Enter Coral IDs** (one per line, or paste column)")
    
    # Generate default coral IDs for convenience
    default_ids = "\n".join([
        f"ACRO-{str(i+1).zfill(3)}" if i < 12 else f"ACRO-{str(i-11).zfill(3)}"
        for i in range(4)
    ])
    
    coral_ids_text = st.text_area("Coral IDs", default_ids, height=300)
    
    # Generate PDF button
    if st.button("Generate Day 0 Data Sheet"):
        coral_ids = [cid.strip() for cid in coral_ids_text.strip().split('\n') if cid.strip()]
        
        try:
            # Assign label as day 0
            day_label = "Day 0"
            
            # Call experiment planner with starting temperature
            pdf_bytes = generate_pdf(exp_name, start_date, day_label, coral_ids, baseline_temp, peak_1_temp)
            
            st.success(f"✅ Data sheet generated successfully!")
            
            # Download button
            filename = f"{exp_name}_Day0_{start_date.strftime('%Y-%m-%d')}.pdf"
            st.download_button(
                label=f"📄 Download Data Sheet",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
            )
            
        except Exception as e:
            st.error(f"Error generating PDF: {e}")

# ==============================================================================
# === PAGE 2: DATASHEET UPLOAD =================================================
# ==============================================================================

elif st.session_state.page == "Datasheet Upload":
    st.title("📷 Datasheet Upload")
    st.write("Upload a photo of a completed data sheet to extract the data.")

    # Upload image file
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

    default_ids = "\n".join([
        f"ACRO-{str(i+1).zfill(3)}" if i < 12 else f"ACRO-{str(i-11).zfill(3)}-C"
        for i in range(4)
    ])
    
    st.write("**Enter Coral IDs** (one per line, or paste column)")

    coral_ids_text = st.text_area("Coral IDs", default_ids, height=300)

    # Process image button
    if st.button("Process Image"):
        if uploaded_file is not None and coral_ids_text.strip():
            coral_ids = [cid.strip() for cid in coral_ids_text.strip().split('\n') if cid.strip()]
            
            with st.spinner("Processing... This may take a moment."):
                try:
                    # Read uploaded file as bytes
                    image_bytes = uploaded_file.read()
                    
                    # Call form digitizer pipeline
                    df, metadata = process_form_image(image_bytes, coral_ids)
                    
                    # Store in session state (persists across re-renders)
                    st.session_state.processed_df = df
                    st.session_state.metadata = metadata
                    st.session_state.csv_filename = f"{metadata['name']}_{metadata['daylabel']}.csv"
                    
                    st.success("✅ Processing Complete!")
                    
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")
                    st.info("Check that the image is clear and all 4 corner markers are visible.")
        else:
            st.warning("Please upload a file and provide Coral IDs.")

    # Display results if they exist in session state
    if 'processed_df' in st.session_state:
        # Display QR Code Metadata
        st.subheader("Experiment Metadata (from QR Code)")

        metadata = st.session_state.get('metadata', {})
                
        # Display in a nice formatted way
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Experiment Name", metadata.get('name', 'not found'))
            st.metric("Date", metadata.get('date', 'N/A'))
        
        with col2:
            st.metric("Day Label", metadata.get('daylabel', 'not found'))
            st.metric("Baseline Temp (°C)", metadata.get('basetemp', 'not found'))
        
        with col3:
            st.metric("Peak Temp (°C)", metadata.get('peaktemp', 'not found'))
        
        st.markdown("---")
        
        st.subheader("Extracted Data")
        
        df = st.session_state.processed_df
        
        # Get the score column name (it's dynamically named based on temperature)
        score_col = [col for col in df.columns if col.startswith('T_') and col.endswith('_Score')]
        score_col = score_col[0] if score_col else 'VBS_Score'
        
        # Calculate data quality metrics
        total_cells = len(df)
        
        empty_cells = df[score_col].isna().sum()
        hyphen_cells = (df[score_col] == '-').sum()
        question_cells = (df[score_col] == '?').sum()
        digit_cells = total_cells - empty_cells - hyphen_cells - question_cells
        
        # Display quality metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Recognized Digits", digit_cells)
        col2.metric("Intentional N/A (-)", hyphen_cells)
        col3.metric("Empty Boxes", empty_cells)
        col4.metric("Needs Review (?)", question_cells)
        
        # Warning for low-confidence predictions
        if question_cells > 0:
            st.warning(f"⚠️ {question_cells} cell(s) flagged for manual review due to low confidence.")
        
        # Show dataframe
        st.dataframe(df)

        # CSV download button
        csv_data = df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Download as CSV",
            data=csv_data,
            file_name=st.session_state.csv_filename,
            mime='text/csv',
        )
    
        st.markdown("---")
        st.subheader("Generate a datasheet for the next day")
        
        if st.button("Generate New Sheet"):
            try:
                # Get metadata from the processed form
                metadata = st.session_state.get('metadata', {})
                
                # Increment day label
                current_day = metadata.get('daylabel', 'Day 0')
                day_num = int(current_day.split()[-1])
                next_day = f"Day {day_num + 1}"
                
                # Get other metadata
                exp_name = metadata.get('name', 'Experiment')
                baseline_temp = metadata.get('basetemp')

                # Calculate recommended next day temp
                current_peak_temp = float(metadata.get('peaktemp'))
                next_peak_temp = calculate_next_ramp(current_peak_temp,df[score_col],day_num)

                # Get current date
                current_date = datetime.strptime(metadata.get('date', ''), '%Y-%m-%d')
                next_date = current_date + timedelta(days=1)
                
                # Get coral IDs from the text area above
                coral_ids = [cid.strip() for cid in coral_ids_text.strip().split('\n') if cid.strip()]
                
                # Generate PDF for next day
                pdf_bytes = generate_pdf(
                    exp_name, 
                    next_date, 
                    next_day, 
                    coral_ids, 
                    baseline_temp, 
                    next_peak_temp
                )
                
                st.success(f"✅ {next_day} data sheet generated successfully!")
                
                # Download button for next day
                filename = f"{exp_name}_{next_day.replace(' ', '')}_{next_date.strftime('%Y-%m-%d')}.pdf"
                st.download_button(
                    label=f"📄 Download {next_day} Data Sheet",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                )
                
            except Exception as e:
                st.error(f"Error generating next day PDF: {e}")