# config.py
"""Configuration constants for the Coral Data Toolkit"""

# --- Form Layout Constants ---
# Letter landscape: 11in wide × 8.5in tall
# Using ~100 DPI for reasonable resolution
DPI = 100
FORM_WIDTH = int(11 * DPI)   # 1100 pixels
FORM_HEIGHT = int(8.5 * DPI)  # 850 pixels

# Layout structure: 4 sheets in 2x2 grid
NUM_SHEETS = 4
SHEETS_COLS = 2
SHEETS_ROWS = 2

# Each sheet has a 4x6 grid
GRID_ROWS = 4
GRID_COLS = 6

# Convert inches to pixels using DPI
def inches_to_pixels(inches):
    return int(inches * DPI)

# --- Sheet positions and dimensions (from HTML template) ---
SHEET_START_X = inches_to_pixels(1)        # 1 inch from left
SHEET_START_Y = inches_to_pixels(2.25)     # 2.25 inches from top
SHEET_WIDTH = inches_to_pixels(4.375)      # 4.375 inches wide (437 pixels)
SHEET_HEIGHT = inches_to_pixels(2.5)       # 2.5 inches tall (250 pixels)
SHEET_GAP_X = inches_to_pixels(0.25)       # 0.25 inch gap (25 pixels)
SHEET_GAP_Y = inches_to_pixels(0.25)       # 0.25 inch gap (25 pixels)

# Within each sheet
SHEET_BORDER = 2  # pixels (border: 2px solid black)
SHEET_PADDING = 5  # pixels (padding: 5px)

# Box title: "Sheet 1", "Sheet 2", etc.
BOX_TITLE_HEIGHT = 15  # pixels (font-size: 9pt + margin-bottom: 3px)

# Table position within sheet
TABLE_START_X = SHEET_BORDER + SHEET_PADDING
TABLE_START_Y = SHEET_BORDER + SHEET_PADDING + BOX_TITLE_HEIGHT

# Cell dimensions - FROM HTML CSS
# From template.html: .sample-table tr { height: 0.59in; }
CELL_HEIGHT = inches_to_pixels(0.59)  # 59 pixels at 100 DPI

# Table width calculation
TABLE_WIDTH = SHEET_WIDTH - (2 * SHEET_BORDER) - (2 * SHEET_PADDING)  # 437 - 4 - 10 = 423
CELL_WIDTH = TABLE_WIDTH / GRID_COLS  # 423 / 6 = 70.5 pixels

# Data entry box: 21pt × 21pt
# From template.html: .data-entry-box { width: 21pt; height: 21pt; }
BOX_SIZE_PT = 21
BOX_WIDTH = inches_to_pixels(BOX_SIZE_PT / 72)   # ~29 pixels
BOX_HEIGHT = inches_to_pixels(BOX_SIZE_PT / 72)  # ~29 pixels

# Box positioning within cell
# From HTML: td { padding: 2px; vertical-align: top; }
# Box has margin: 2px auto 0 auto (2px gap from text above)
CELL_PADDING = 2  # pixels
TEXT_RENDERED_HEIGHT = 10  # pixels (7pt font rendered)
BOX_TOP_MARGIN = 2  # pixels (margin between text and box)

# Box is centered horizontally in cell
BOX_OFFSET_X = (CELL_WIDTH - BOX_WIDTH) / 2

# Box is positioned below text at top of cell
BOX_OFFSET_Y = CELL_PADDING + TEXT_RENDERED_HEIGHT + BOX_TOP_MARGIN  # 2 + 10 + 2 = 14 pixels

# --- OCR Configuration ---
DIGIT_MODEL_PATH = 'digit_model.h5'
CONFIDENCE_THRESHOLD = 0.6
EMPTY_BOX_THRESHOLD = 0.05
MIN_CONTOUR_AREA = 10

# Margin for cropping out the square border of the boxes:
BORDER_CROP_MARGIN = 4  # pixels
