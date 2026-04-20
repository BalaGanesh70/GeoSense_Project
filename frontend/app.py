import streamlit as st
import requests
import cv2
import numpy as np
import os
import re
import difflib
try:
    import pandas as pd
except Exception:
    pd = None
try:
    import pytesseract
except ImportError:
    pytesseract = None

INDIA_STATES_UT = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands",
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry"
]

UNION_TERRITORIES = {
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
}

INDIA_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", "Surat",
    "Pune", "Jaipur", "Lucknow", "Kanpur", "Nagpur", "Visakhapatnam", "Bhopal", "Patna",
    "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot",
    "Kalyan", "Vasai", "Varanasi", "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Navi Mumbai",
    "Prayagraj", "Ranchi", "Howrah", "Coimbatore", "Jabalpur", "Gwalior", "Vijayawada", "Jodhpur",
    "Madurai", "Raipur", "Kota", "Guwahati", "Chandigarh", "Thiruvananthapuram", "Mysuru", "Noida",
    "Jalandhar", "Bhubaneswar", "Salem", "Warangal", "Guntur", "Bhiwandi", "Saharanpur", "Gorakhpur",
    "Bikaner", "Amravati", "Nanded", "Kolhapur", "Ajmer", "Ujjain", "Tiruppur", "Bhilai", "Bilaspur",
    "Dehradun", "Jammu", "Udaipur", "Mangalore", "Belagavi", "Tiruchirappalli", "Ernakulam", "Kochi",
    "Aligarh", "Bareilly", "Moradabad", "Siliguri", "Asansol", "Rourkela", "Jamshedpur", "Durgapur",
    "Bhavnagar", "Jamnagar", "Anand", "Nellore", "Kurnool", "Tirunelveli", "Thoothukudi", "Erode",
    "Puducherry", "Shimla", "Panaji", "Imphal", "Aizawl", "Kohima", "Shillong", "Gangtok", "Agartala",
    "Itanagar", "Port Blair", "Leh"
]


def _build_india_admin_rows() -> list[dict]:
    rows = []
    for idx, name in enumerate(sorted(INDIA_STATES_UT), start=1):
        admin_type = "Union Territory" if name in UNION_TERRITORIES else "State"
        rows.append(
            {
                "S.No": idx,
                "Name": name,
                "Type": admin_type,
                "Code": f"IN-{idx:02d}",
                "Initial": name[0].upper(),
            }
        )
    return rows


def enhance_satellite_for_human_view(image_bytes: bytes) -> bytes:
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")

    # Improve local contrast on luminance channel (satellite -> more human-viewable)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    contrast_img = cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2BGR)

    # Mild denoise + sharpening for clearer edges
    denoised = cv2.bilateralFilter(contrast_img, d=7, sigmaColor=35, sigmaSpace=35)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    enhanced = cv2.filter2D(denoised, -1, sharpen_kernel)

    ok, encoded = cv2.imencode(".png", enhanced)
    if not ok:
        raise ValueError("Could not encode enhanced image.")
    return encoded.tobytes()


def _ocr_text(image_bgr: np.ndarray) -> str:
    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed.")
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return pytesseract.image_to_string(th, config="--oem 3 --psm 6").strip()


def _clean_text(text: str) -> str:
    text = re.sub(r"[^A-Za-z\s-]", " ", text)
    text = " ".join(text.split())
    return text.strip()


def _match_indian_state(text: str, cutoff: float = 0.78) -> str:
    clean = _clean_text(text).title()
    if not clean:
        return ""
    candidates = difflib.get_close_matches(clean, INDIA_STATES_UT, n=1, cutoff=cutoff)
    return candidates[0] if candidates else ""


def _extract_indian_states_from_text(text: str, cutoff: float = 0.86) -> list[str]:
    clean = _clean_text(text)
    if not clean:
        return []
    words = clean.split()
    chunks = set()
    for n in (1, 2, 3, 4, 5):
        for i in range(len(words) - n + 1):
            chunks.add(" ".join(words[i:i + n]))
    matches = set()
    for chunk in chunks:
        m = _match_indian_state(chunk, cutoff=cutoff)
        if m:
            matches.add(m)
    return sorted(matches)


def _normalize_city_candidate(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    tokens = [t for t in cleaned.split() if len(t) > 1]
    if not tokens or len(tokens) > 3:
        return ""
    if any(len(t) > 18 for t in tokens):
        return ""
    # Reject obviously noisy OCR snippets.
    blacklist = {"aa", "ae", "af", "ah", "al", "as", "iv", "iy", "ns", "of", "on", "ye"}
    if len(tokens) == 1 and tokens[0].lower() in blacklist:
        return ""
    name = " ".join(tokens).title()
    return name if len(name) >= 3 else ""


def _extract_indian_cities_from_text(text: str, cutoff: float = 0.86) -> list[str]:
    clean = _clean_text(text)
    if not clean:
        return []
    words = clean.split()
    chunks = set()
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            chunks.add(" ".join(words[i:i + n]))
    matches = set()
    for chunk in chunks:
        candidate = _normalize_city_candidate(chunk)
        if not candidate:
            continue
        matched = difflib.get_close_matches(candidate, INDIA_CITIES, n=1, cutoff=cutoff)
        if matched:
            matches.add(matched[0])
    return sorted(matches)


def _ocr_candidates(image_bgr: np.ndarray) -> list[str]:
    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed.")

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 7, 40, 40)
    th_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    th_adapt = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 8
    )

    variants = [gray, th_otsu, th_adapt]
    candidates: list[str] = []
    for variant in variants:
        scaled = cv2.resize(variant, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        for psm in (6, 7, 11):
            config = f"--oem 3 --psm {psm} -l eng"
            text = pytesseract.image_to_string(scaled, config=config)
            clean = _clean_text(text)
            if len(clean) >= 3:
                candidates.append(clean)
    return candidates


def _extract_country_state(full_image_bgr: np.ndarray) -> tuple[str, str]:
    candidates = _ocr_candidates(full_image_bgr)
    all_text = "\n".join(candidates)
    country = ""
    state = ""
    for line in all_text.splitlines():
        lower = line.lower()
        if "country" in lower:
            country = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
        if "state" in lower:
            value = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
            state = _match_indian_state(value) or value
    if not state:
        state_matches = _extract_indian_states_from_text(all_text, cutoff=0.90)
        state = state_matches[0] if state_matches else ""
    return _clean_text(country), _clean_text(state)


def detect_cities_from_green_boxes(image_bytes: bytes) -> tuple[np.ndarray, list[str], str, str]:
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image for city detection.")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 40], dtype=np.uint8)
    upper_green = np.array([90, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_green, upper_green)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    annotated = img.copy()
    city_candidates = set()

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 25 or h < 25:
            continue
        pad = 4
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img.shape[1], x + w + pad)
        y2 = min(img.shape[0], y + h + pad)
        roi = img[y1:y2, x1:x2]

        roi_candidates = _ocr_candidates(roi)
        for label in roi_candidates:
            for city_name in _extract_indian_cities_from_text(label, cutoff=0.88):
                city_candidates.add(city_name)

        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Fallback: if green-box OCR fails, try full-image OCR matching.
    if not city_candidates:
        full_candidates = _ocr_candidates(img)
        for text in full_candidates:
            for city_name in _extract_indian_cities_from_text(text, cutoff=0.82):
                city_candidates.add(city_name)

    # Secondary fallback with enhanced image for faint labels.
    if not city_candidates:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l2 = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2BGR)
        for text in _ocr_candidates(enhanced):
            for city_name in _extract_indian_cities_from_text(text, cutoff=0.80):
                city_candidates.add(city_name)

    country, state = _extract_country_state(img)
    return annotated, sorted(city_candidates), country, state


def detect_states_from_green_boxes(image_bytes: bytes) -> tuple[np.ndarray, list[str]]:
    """
    Detects Indian state/UT names that appear inside green boxed labels.
    OCRs the label text and fuzzy-matches to INDIA_STATES_UT (no fixed results).
    """
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image for state detection.")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 40], dtype=np.uint8)
    upper_green = np.array([90, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_green, upper_green)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    annotated = img.copy()
    matches = set()

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 25 or h < 25:
            continue

        pad = 4
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img.shape[1], x + w + pad)
        y2 = min(img.shape[0], y + h + pad)
        roi = img[y1:y2, x1:x2]

        for cand in _ocr_candidates(roi):
            for st_name in _extract_indian_states_from_text(cand, cutoff=0.82):
                matches.add(st_name)

        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)

    if not matches:
        for cand in _ocr_candidates(img):
            for st_name in _extract_indian_states_from_text(cand, cutoff=0.84):
                matches.add(st_name)

    return annotated, sorted(matches)


st.title("GeoSense AI 🌍")

if "view" not in st.session_state:
    st.session_state.view = "input"
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = {}
if "upload_bytes" not in st.session_state:
    st.session_state.upload_bytes = None
if "upload_name" not in st.session_state:
    st.session_state.upload_name = None
if "show_states_table" not in st.session_state:
    st.session_state.show_states_table = False
if "greenbox_states" not in st.session_state:
    st.session_state.greenbox_states = []
if "greenbox_states_img" not in st.session_state:
    st.session_state.greenbox_states_img = None

uploaded_file = st.file_uploader("Upload Satellite Image", key="geosense_main_file_uploader")
if uploaded_file is not None:
    st.session_state.upload_bytes = uploaded_file.getvalue()
    st.session_state.upload_name = uploaded_file.name or "upload.png"

raw_bytes = st.session_state.upload_bytes
has_upload = raw_bytes is not None

if has_upload:
    _h1, _h2 = st.columns([4, 1])
    with _h2:
        if st.button("Clear upload", help="Remove image and analysis from this session"):
            st.session_state.upload_bytes = None
            st.session_state.upload_name = None
            st.session_state.analysis_data = None
            st.session_state.view = "input"
            st.session_state.greenbox_states_img = None
            st.session_state.greenbox_states = []
            st.session_state.show_states_table = False
            st.rerun()

    st.caption(f"Image in session: **{st.session_state.upload_name or 'upload'}** — stays available when you use other pages.")

    st.subheader("OCR Setup (Windows)")
    if pytesseract is None:
        st.info("Install: `pip install pytesseract` and install the Tesseract OCR app on Windows.")
    else:
        # Try to auto-detect a common Tesseract install location
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        default_path = next((p for p in common_paths if os.path.exists(p)), "")
        tesseract_path = st.text_input(
            "Path to tesseract.exe",
            value=default_path,
            placeholder=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        )
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        st.caption(f"Current tesseract path: `{getattr(pytesseract.pytesseract, 'tesseract_cmd', '')}`")
        if tesseract_path and not os.path.exists(tesseract_path):
            st.warning("The provided tesseract.exe path does not exist.")

        # Self-check: tell user exactly what's wrong instead of generic message
        try:
            ver = pytesseract.get_tesseract_version()
            st.success(f"Tesseract detected: {ver}")
        except Exception as e:
            st.error("Tesseract is not working yet.")
            st.code(str(e))

    st.subheader("Original Image")
    st.image(raw_bytes)

    use_enhanced = st.checkbox(
        "Convert to clearer human-view style before analysis",
        value=False,
        key="geosense_use_enhanced_preview",
    )
    image_to_send = raw_bytes

    if use_enhanced:
        try:
            enhanced_bytes = enhance_satellite_for_human_view(raw_bytes)
            st.subheader("Enhanced Human-View Preview")
            st.image(enhanced_bytes)
            image_to_send = enhanced_bytes
        except ValueError as e:
            st.error(f"Image enhancement failed: {e}")
            st.stop()

    st.subheader("City Detection (Green Boxes)")

    b1, b2 = st.columns([1, 1])
    with b1:
        if st.button("Detect States in Green Boxes"):
            try:
                ann, states = detect_states_from_green_boxes(raw_bytes)
                st.session_state.greenbox_states_img = ann
                st.session_state.greenbox_states = states
                st.session_state.show_states_table = True
            except Exception as e:
                st.error(str(e))
    with b2:
        if st.button("Show India States/UTs Table"):
            st.session_state.show_states_table = True

    if st.session_state.greenbox_states_img is not None:
        st.markdown("**Detected States/UTs from Green Boxes**")
        st.image(
            cv2.cvtColor(st.session_state.greenbox_states_img, cv2.COLOR_BGR2RGB),
            caption="Detected green boxes",
        )
        if st.session_state.greenbox_states:
            st.write(st.session_state.greenbox_states)

    if st.session_state.show_states_table:
        try:
            # Per your request: show hardcoded Indian states/UTs in a professional table view.
            rows = _build_india_admin_rows()
            total = len(rows)
            total_states = sum(1 for r in rows if r["Type"] == "State")
            total_uts = sum(1 for r in rows if r["Type"] == "Union Territory")

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Regions", total)
            col2.metric("States", total_states)
            col3.metric("Union Territories", total_uts)

            search_term = st.text_input("Search by name", value="", key="states_search").strip().lower()
            type_filter = st.selectbox(
                "Filter by type",
                ["All", "State", "Union Territory"],
                index=0,
                key="states_type_filter",
            )

            filtered = rows
            if type_filter != "All":
                filtered = [r for r in filtered if r["Type"] == type_filter]
            if search_term:
                filtered = [r for r in filtered if search_term in r["Name"].lower()]

            st.dataframe(filtered, use_container_width=True, hide_index=True)

            csv_lines = ["S.No,Name,Type,Code,Initial"]
            for r in filtered:
                csv_lines.append(f"{r['S.No']},{r['Name']},{r['Type']},{r['Code']},{r['Initial']}")
            csv_data = "\n".join(csv_lines)
            st.download_button(
                "Download Table as CSV",
                data=csv_data,
                file_name="india_states_uts.csv",
                mime="text/csv",
            )
        except RuntimeError as e:
            st.error(str(e))
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error("OCR failed with an unexpected error.")
            st.code(str(e))

    if st.button("Analyze"):
        files = {
            "file": (st.session_state.upload_name or "upload.png", image_to_send, "image/png")
        }
        try:
            response = requests.post("http://localhost:8000/analyze", files=files, timeout=120)
        except requests.RequestException as e:
            st.error(f"Backend request failed: {e}")
            st.stop()

        if not response.ok:
            st.error(f"Backend returned {response.status_code}")
            if response.text:
                st.code(response.text)
            st.stop()

        try:
            data = response.json()
        except ValueError:
            st.error("Backend did not return JSON.")
            if response.text:
                st.code(response.text)
            st.stop()

        st.session_state.analysis_data = data
        st.session_state.view = "results"

    if st.session_state.view == "results" and st.session_state.analysis_data:
        st.success(
            "Analysis completed. You can stay on this page or open a report from the sidebar "
            "(Affected Regions, Reasons / Causes, etc.)."
        )
        p1, p2 = st.columns(2)
        with p1:
            st.page_link("pages/1_Affected_Regions.py", label="Affected Regions", icon="🗺️")
        with p2:
            st.page_link("pages/2_Reasons.py", label="Reasons / Causes (Core Disaster Snapshot)", icon="📊")