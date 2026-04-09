# form_digitizer.py
"""Functions for processing and digitizing completed data collection forms"""

import cv2
import numpy as np
import json
import pandas as pd
from tensorflow.keras.models import load_model
import streamlit as st
from config import *


@st.cache_resource
def load_digit_model():
    """Loads the pre-trained handwritten digit recognition model."""
    try:
        return load_model(DIGIT_MODEL_PATH)
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None


def find_and_warp_sheet(image):
    """Finds 4 ArUco markers and straightens the image, preserving full page dimensions."""
    if image is None:
        raise FileNotFoundError("Could not read the uploaded image.")

    # Load ArUco dictionary and create detector
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Detect markers
    corners, ids, rejected = detector.detectMarkers(image)
    
    # Debug: draw detected markers
    # debug_image = image.copy()
    # if ids is not None:
    #     cv2.aruco.drawDetectedMarkers(debug_image, corners, ids)
    # cv2.imwrite('debug_aruco.jpg', debug_image)
    
    if ids is None or len(ids) != 4:
        raise Exception(f"Expected 4 ArUco markers, found {0 if ids is None else len(ids)}. "
                        "Check that all corner markers are visible and the image is clear.")
    
    # Get centers of each marker
    marker_centers = {}
    for i, corner in enumerate(corners):
        marker_id = ids[i][0]
        center_x = np.mean(corner[0][:, 0])
        center_y = np.mean(corner[0][:, 1])
        marker_centers[marker_id] = [center_x, center_y]
    
    # Verify we have all 4 expected markers (IDs 0, 1, 2, 3)
    required_ids = {0, 1, 2, 3}
    found_ids = set(marker_centers.keys())
    if not required_ids.issubset(found_ids):
        missing = required_ids - found_ids
        raise Exception(f"Missing ArUco markers with IDs: {missing}")
    
    # ArUco marker layout:
    # - Each marker is 0.4in × 0.4in
    # - Top-left corner of each marker is positioned 0.3in from page edges
    # - Therefore, the CENTER of each marker is at:
    #   * 0.3in (edge to marker corner) + 0.2in (half of marker) = 0.5in from edges
    
    marker_edge_offset = inches_to_pixels(0.3)      # Distance from page edge to marker edge
    marker_half_size = inches_to_pixels(0.4) / 2    # Half the marker size
    marker_center_offset = marker_edge_offset + marker_half_size  # Distance from page edge to marker center
    
    # Source points: actual marker centers in the photo
    src_pts = np.float32([
        marker_centers[0],  # Top-left
        marker_centers[1],  # Top-right
        marker_centers[3],  # Bottom-right
        marker_centers[2]   # Bottom-left
    ])
    
    # Destination points: where marker CENTERS should be in the warped image
    dst_pts = np.float32([
        [marker_center_offset, marker_center_offset],                                      # Top-left
        [FORM_WIDTH - marker_center_offset, marker_center_offset],                         # Top-right
        [FORM_WIDTH - marker_center_offset, FORM_HEIGHT - marker_center_offset],          # Bottom-right
        [marker_center_offset, FORM_HEIGHT - marker_center_offset]                         # Bottom-left
    ])
    
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(image, matrix, (FORM_WIDTH, FORM_HEIGHT))
    return warped


def read_qr_code(warped_image):
    """Reads and decodes the QR code - searches the entire image."""
    detector = cv2.QRCodeDetector()
    
    # Try on full image (color)
    data, vertices, _ = detector.detectAndDecode(warped_image)
    if data:
        return json.loads(data)
    
    # Try grayscale
    gray = cv2.cvtColor(warped_image, cv2.COLOR_BGR2GRAY)
    data, vertices, _ = detector.detectAndDecode(gray)
    if data:
        return json.loads(data)
    
    # Try with binary threshold
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    data, vertices, _ = detector.detectAndDecode(binary)
    if data:
        return json.loads(data)
    
    # Try with adaptive threshold
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
    data, vertices, _ = detector.detectAndDecode(adaptive)
    if data:
        return json.loads(data)
    
    # Last resort: try increasing image resolution
    scaled_up = cv2.resize(warped_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    data, vertices, _ = detector.detectAndDecode(scaled_up)
    if data:
        return json.loads(data)
    
    # Save debug images if all methods fail
    # cv2.imwrite('debug_qr_gray.jpg', gray)
    # cv2.imwrite('debug_qr_binary.jpg', binary)
    # cv2.imwrite('debug_qr_adaptive.jpg', adaptive)
    
    raise Exception("QR Code not found after trying multiple detection methods. "
                   "Check debug images: debug_warped_sheet.jpg, debug_qr_gray.jpg, debug_qr_binary.jpg")


def recognize_digit(roi, model):
    """Returns: None (empty), '-' (hyphen), 0-9 (digit), or '?' (low confidence)"""
    if model is None:
        return '?'
    
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Use adaptive thresholding instead of Otsu
    thresh = cv2.adaptiveThreshold(
        gray, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        blockSize=11,  # Size of neighborhood (must be odd)
        C=2  # Constant subtracted from mean
    )
    
    # cv2.imwrite('debug_thresh_adaptive.jpg', thresh)
    
    pixel_density = np.sum(thresh) / (thresh.size * 255)
    if pixel_density < EMPTY_BOX_THRESHOLD:
        return None    


    if np.sum(thresh) / (thresh.size * 255) < EMPTY_BOX_THRESHOLD:
        return None
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    
    contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(contour)
    
    if w < 5 or h < 5 or cv2.contourArea(contour) < MIN_CONTOUR_AREA:
        return None
    
    digit = thresh[y:y+h, x:x+w]
    dh, dw = digit.shape
    pad = int(abs(dh - dw) / 2)
    digit = cv2.copyMakeBorder(digit, 0, 0, pad, pad, cv2.BORDER_CONSTANT) if dh > dw else \
            cv2.copyMakeBorder(digit, pad, pad, 0, 0, cv2.BORDER_CONSTANT)
    
    digit = cv2.resize(digit, (20, 20))
    digit = cv2.copyMakeBorder(digit, 4, 4, 4, 4, cv2.BORDER_CONSTANT)
    digit = (digit.astype('float32') / 255.0).reshape(1, 28, 28, 1)
    
    pred = model.predict(digit, verbose=0)
    cls, conf = np.argmax(pred), np.max(pred)
    
    if conf < CONFIDENCE_THRESHOLD:
        return '?'
    return '-' if cls == 6 else int(cls + 1)


def get_data_box_coordinates(sheet_idx, row_idx, col_idx):
    """Calculate approximate pixel coordinates for a data entry box (coarse estimate)."""
    # Determine which sheet (0-3) in the 2x2 grid
    sheet_row = sheet_idx // SHEETS_COLS  # 0 or 1
    sheet_col = sheet_idx % SHEETS_COLS   # 0 or 1
    
    # Sheet top-left corner (absolute position on page)
    sheet_x = SHEET_START_X + sheet_col * (SHEET_WIDTH + SHEET_GAP_X)
    sheet_y = SHEET_START_Y + sheet_row * (SHEET_HEIGHT + SHEET_GAP_Y)
    
    # Table top-left corner (relative to sheet)
    table_x = sheet_x + TABLE_START_X
    table_y = sheet_y + TABLE_START_Y
    
    # Cell top-left corner (using FLOAT arithmetic to avoid cumulative rounding)
    cell_x = table_x + (col_idx * CELL_WIDTH)
    cell_y = table_y + (row_idx * CELL_HEIGHT)
    
    # Data box position (within the cell)
    box_x = cell_x + BOX_OFFSET_X
    box_y = cell_y + BOX_OFFSET_Y
    
    # Return as integers for pixel indexing
    return int(box_x), int(box_y), int(BOX_WIDTH), int(BOX_HEIGHT)


def refine_box_location(image, approx_x, approx_y, approx_w, approx_h, search_radius=10):
    """
    Refine the box location by detecting the actual box edges.
    
    Args:
        image: Grayscale or color image
        approx_x, approx_y, approx_w, approx_h: Approximate box coordinates
        search_radius: How many pixels to search around the approximate location
        
    Returns:
        (refined_x, refined_y, refined_w, refined_h) or original if detection fails
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Define search area (expand around approximate location)
    search_x1 = max(0, approx_x - search_radius)
    search_y1 = max(0, approx_y - search_radius)
    search_x2 = min(gray.shape[1], approx_x + approx_w + search_radius)
    search_y2 = min(gray.shape[0], approx_y + approx_h + search_radius)
    
    # Extract search region
    search_region = gray[search_y1:search_y2, search_x1:search_x2]
    
    # Edge detection to find the box
    edges = cv2.Canny(search_region, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        # No box found, return original coordinates
        return approx_x, approx_y, approx_w, approx_h
    
    # Find contours that are roughly square and near the expected size
    best_box = None
    best_score = float('inf')
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # Check if size is reasonable (within 50% of expected)
        size_match = abs(w - approx_w) < approx_w * 0.5 and abs(h - approx_h) < approx_h * 0.5
        
        # Check if roughly square
        aspect_ratio = w / h if h > 0 else 0
        is_square = 0.7 < aspect_ratio < 1.3
        
        # Check if near expected location
        center_x = x + w // 2
        center_y = y + h // 2
        expected_center_x = approx_x - search_x1 + approx_w // 2
        expected_center_y = approx_y - search_y1 + approx_h // 2
        distance = np.sqrt((center_x - expected_center_x)**2 + (center_y - expected_center_y)**2)
        
        if size_match and is_square and distance < search_radius * 2:
            # Score based on distance to expected location
            if distance < best_score:
                best_score = distance
                best_box = (x + search_x1, y + search_y1, w, h)
    
    if best_box is not None:
        return best_box
    else:
        # Return original if no good box found
        return approx_x, approx_y, approx_w, approx_h


def extract_table_data(warped_image, coral_ids, model):
    """Extracts data from all 4 sheets (6x4 grids each) with box refinement."""
    results = []
    
    # Create debug images
    # debug_coarse = cv2.cvtColor(warped_image.copy(), cv2.COLOR_BGR2RGB)
    # debug_refined = cv2.cvtColor(warped_image.copy(), cv2.COLOR_BGR2RGB)
    
    for sheet_idx in range(NUM_SHEETS):
        # Each sheet handles 6 coral IDs
        sheet_coral_start = sheet_idx * 6
        
        for col_idx in range(GRID_COLS):
            coral_idx = sheet_coral_start + col_idx
            
            # Skip if we don't have a coral ID for this column
            if coral_idx >= len(coral_ids):
                continue
            
            coral_id = coral_ids[coral_idx]
            
            # Extract all 4 rows for this column
            for row_idx in range(GRID_ROWS):
                # Step 1: Get approximate coordinates
                approx_x, approx_y, approx_w, approx_h = get_data_box_coordinates(sheet_idx, row_idx, col_idx)
                
                # Draw approximate box in blue on debug image
                # cv2.rectangle(debug_coarse, (approx_x, approx_y), 
                #             (approx_x + approx_w, approx_y + approx_h), (0, 0, 255), 1)
                
                # Step 2: Refine box location by detecting actual edges
                refined_x, refined_y, refined_w, refined_h = refine_box_location(
                    warped_image, approx_x, approx_y, approx_w, approx_h, search_radius=15
                )
                
                # Draw refined box in green on debug image
                # cv2.rectangle(debug_refined, (refined_x, refined_y), 
                #             (refined_x + refined_w, refined_y + refined_h), (0, 255, 0), 1)

                # Crop out border of box:
                refined_x = refined_x + BORDER_CROP_MARGIN
                refined_y = refined_y + BORDER_CROP_MARGIN
                refined_w = refined_w - (2 * BORDER_CROP_MARGIN)
                refined_h = refined_h - (2 * BORDER_CROP_MARGIN)
                
                # Extract ROI using refined coordinates
                roi = warped_image[refined_y:refined_y+refined_h, refined_x:refined_x+refined_w]
                
                # Recognize digit
                score = recognize_digit(roi, model)
                
                # Determine label based on row
                if row_idx == 0:
                    replicate = "Heated_A"
                    sample_type = "H"
                elif row_idx == 1:
                    replicate = "Control_A"
                    sample_type = "C"
                elif row_idx == 2:
                    replicate = "Heated_B"
                    sample_type = "H"
                else:  # row_idx == 3
                    replicate = "Control_B"
                    sample_type = "C"
                
                results.append({
                    'Sheet': sheet_idx + 1,
                    'Coral_ID': coral_id,
                    'Replicate': replicate,
                    'Treatment': sample_type,
                    'VBS_Score': score
                })
    
    # Save debug images
    # cv2.imwrite('debug_boxes_coarse.jpg', debug_coarse)
    # cv2.imwrite('debug_boxes_refined.jpg', debug_refined)
    
    return results


def process_form_image(image_bytes, coral_ids):
    """Complete pipeline to process a form image and return DataFrame."""
    model = load_digit_model()
    if model is None:
        raise Exception("Could not load digit recognition model")
    
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    
    # Step 1: Warp image
    warped = find_and_warp_sheet(image)
    
    # Step 2: Read QR code
    metadata = read_qr_code(warped)
    
    # Print QR code contents for debugging
    #print("=" * 50)
    #print("QR Code detected successfully!")
    #print("QR Code contents:")
    #for key, value in metadata.items():
    #    print(f"  {key}: {value}")
    #print("=" * 50)
    
    # Step 3: Extract table data
    table_data = extract_table_data(warped, coral_ids, model)
    
    # Step 4: Create DataFrame
    df = pd.DataFrame(table_data)

    # Insert metadata from QR code
    df.insert(0, 'Experiment ID', metadata.get('name', 'Unknown'))
    df.insert(1, 'Date', metadata.get('date', ''))

    if 'VBS_Score' in df.columns and metadata['daylabel'] == 'Day 0':
        df.rename(columns={'VBS_Score': f'T_{metadata['basetemp']}_Score'}, inplace=True)
    else:
        df.rename(columns={'VBS_Score': f'T_{metadata['peaktemp']}_Score'}, inplace=True)


    return df, metadata