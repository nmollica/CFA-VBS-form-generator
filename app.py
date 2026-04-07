import streamlit as st
import qrcode
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import json
import base64
from io import BytesIO

# --- 1. SET UP THE USER INTERFACE ---
st.title("Coral Data Sheet Generator")

# Get user inputs
exp_id = st.text_input("Experiment ID", "W24-R3")
exp_date = st.date_input("Date")
# Use a text area for a list of coral IDs, one per line
coral_ids_text = st.text_area("Coral IDs (one per line)", "ACRO-001\nACRO-002\nPORI-015")
coral_ids = coral_ids_text.strip().split('\n')

# --- 2. THE LOGIC WHEN THE BUTTON IS CLICKED ---
if st.button("Generate Printable PDF"):
    # Create a dictionary of data for the QR code
    qr_data = {
        "experiment_id": exp_id,
        "date": exp_date.strftime("%Y-%m-%d"),
        "num_corals": len(coral_ids)
    }

    # Generate QR code and save it as an in-memory image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # To use the image in HTML, we embed it using base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    qr_code_path = f"data:image/png;base64,{img_str}"

    # --- 3. RENDER THE HTML TEMPLATE ---
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("template.html")

    html_out = template.render(
        experiment_id=exp_id,
        date=exp_date.strftime("%B %d, %Y"),
        coral_ids=coral_ids,
        qr_code_path=qr_code_path
    )

    # --- 4. CONVERT HTML TO PDF IN MEMORY ---
    pdf_bytes = HTML(string=html_out).write_pdf()

    # --- 5. PROVIDE PDF FOR DOWNLOAD ---
    st.success("PDF Generated Successfully!")
    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name=f"{exp_id}_{exp_date.strftime('%Y-%m-%d')}.pdf",
        mime="application/pdf",
    )