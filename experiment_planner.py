# experiment_planner.py
"""Functions for planning experiments and generating data collection forms"""

import json
import qrcode
import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


def create_qr_code(metadata):
    """Creates a QR code containing experiment metadata."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(metadata))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def generate_aruco_marker(marker_id, size=100):
    """Generate an ArUco marker image as base64 data URI."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size)
    
    # Convert to PIL Image
    pil_img = Image.fromarray(marker_image)
    
    # Convert to base64
    buffered = BytesIO()
    pil_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def generate_pdf(experiment_id, date, day_label, coral_ids, baseline_temperature, new_peak_temperature):
    """Generates a 2-page PDF for data collection."""
    # Create QR code with experiment metadata
    qr_data = {
        "name": experiment_id,
        "date": date.strftime("%Y-%m-%d"),
        "daylabel": day_label,
        "basetemp": baseline_temperature,
        "peaktemp": new_peak_temperature
    }
    
    qr_code_path = create_qr_code(qr_data)
    
    # Generate ArUco markers for the four corners
    # IDs: 0=Top-Left, 1=Top-Right, 2=Bottom-Left, 3=Bottom-Right
    aruco_tl = generate_aruco_marker(0, size=120)
    aruco_tr = generate_aruco_marker(1, size=120)
    aruco_bl = generate_aruco_marker(2, size=120)
    aruco_br = generate_aruco_marker(3, size=120)
    
    # Render template
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("template.html")
    
    html_out = template.render(
        experiment_id=experiment_id,
        date=date.strftime("%B %d, %Y"),
        day=day_label,
        coral_ids=coral_ids,
        qr_code_path=qr_code_path,
        baseline_temperature=baseline_temperature,
        new_peak_temperature=new_peak_temperature,
        aruco_tl=aruco_tl,
        aruco_tr=aruco_tr,
        aruco_bl=aruco_bl,
        aruco_br=aruco_br
    )
    
    return HTML(string=html_out).write_pdf()