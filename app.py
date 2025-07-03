import streamlit as st
import os
import zipfile
import shutil
from pathlib import Path
import humanfriendly
import uuid
from io import BytesIO

# --- Setup persistent session directory ---
SESSION_ID = st.session_state.get("session_id", str(uuid.uuid4()))
st.session_state["session_id"] = SESSION_ID
BASE_TEMP_DIR = f"temp_storage_{SESSION_ID}"
INPUT_DIR = os.path.join(BASE_TEMP_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_TEMP_DIR, "output")
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Set page config ---
st.set_page_config(
    page_title="Smart Folder Chunker", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for Light Theme ---
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #dad0f7;
    }
    
    /* Header container */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0;
        margin-bottom: 2rem;
    }
    
    /* Logo styling */
    .logo {
        font-size: 2.5rem;
        font-weight: bold;
        color: #000000;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    /* Reset button styling */
    .reset-button {
        background-color: #ffffff;
        border: 2px solid #000000;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 18px;
        font-weight: bold;
        color: #000000;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
    }
    
    .reset-button:hover {
        background-color: #f0f0f0;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Chunk size container */
    .chunk-size-container {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #000000;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .chunk-size-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #000000;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    /* Predefined buttons */
    .size-buttons {
        display: flex;
        gap: 10px;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 1rem;
    }
    
    .size-btn {
        background-color: #ffffff;
        border: 2px solid #000000;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: bold;
        color: #000000;
        cursor: pointer;
        transition: all 0.3s ease;
        min-width: 60px;
    }
    
    .size-btn:hover {
        background-color: #e0e0e0;
        transform: translateY(-1px);
    }
    
    .size-btn.active {
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Upload area styling */
    .upload-container {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        border: 3px dashed #000000;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Process button */
    .process-btn {
        background-color: #000000;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 12px 30px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        margin: 1rem 0;
    }
    
    .process-btn:hover {
        background-color: #333333;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    
    /* Results container */
    .results-container {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #000000;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Download buttons */
    .download-btn {
        background-color: #ffffff;
        border: 2px solid #000000;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: bold;
        color: #000000;
        margin: 4px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .download-btn:hover {
        background-color: #f0f0f0;
        transform: translateY(-1px);
    }
    
    /* Hide Streamlit elements */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    
    /* Custom input styling */
    .stTextInput > div > div > input {
        border: 2px solid #000000;
        border-radius: 8px;
        padding: 8px 12px;
        font-weight: bold;
        color: #000000;
        background-color: #ffffff;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #666666;
        box-shadow: 0 0 0 2px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- Utility Functions ---
def get_folder_size(folder_path):
    total = 0
    for dirpath, _, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total += os.path.getsize(filepath)
    return total

def create_zip_from_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(folder_path.parent)
                zipf.write(file_path, arcname)

def create_zip_from_files(files, zip_path, base_folder):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            arcname = file_path.relative_to(base_folder.parent)
            zipf.write(file_path, arcname)

def split_large_folder(folder_path, folder_name, max_size, output_dir):
    files = [f for f in folder_path.rglob('*') if f.is_file()]
    chunks, current_chunk, current_size, part_num = [], [], 0, 1

    for file in files:
        file_size = os.path.getsize(file)
        if current_size + file_size > max_size and current_chunk:
            zip_name = f"{folder_name}_part{part_num}.zip"
            zip_path = os.path.join(output_dir, zip_name)
            create_zip_from_files(current_chunk, zip_path, folder_path)
            chunks.append(zip_name)
            current_chunk, current_size, part_num = [], 0, part_num + 1

        current_chunk.append(file)
        current_size += file_size

    if current_chunk:
        zip_name = f"{folder_name}_part{part_num}.zip"
        zip_path = os.path.join(output_dir, zip_name)
        create_zip_from_files(current_chunk, zip_path, folder_path)
        chunks.append(zip_name)

    return chunks

def split_folder_intelligently(input_folder, max_chunk_size, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    subfolders = [f for f in Path(input_folder).iterdir() if f.is_dir()]
    results = []

    for subfolder in subfolders:
        folder_name = subfolder.name
        folder_size = get_folder_size(subfolder)

        if folder_size <= max_chunk_size:
            zip_name = f"{folder_name}.zip"
            zip_path = os.path.join(output_dir, zip_name)
            create_zip_from_folder(subfolder, zip_path)
            results.append({'original': folder_name, 'chunks': [zip_name], 'size': folder_size})
        else:
            parts = split_large_folder(subfolder, folder_name, max_chunk_size, output_dir)
            results.append({'original': folder_name, 'chunks': parts, 'size': folder_size})
    return results

# --- Header with Logo and Reset Button ---
st.markdown("""
    <div class="header-container">
        <div class="logo">🗂️ SMART FOLDER CHUNKER</div>
        <div></div>
    </div>
""", unsafe_allow_html=True)

# Reset button in top right
col1, col2, col3 = st.columns([6, 1, 1])
with col3:
    if st.button("🔄 RESET", key="reset_btn", help="Reset current session"):
        if "zip_results" in st.session_state:
            del st.session_state["zip_results"]
        if "session_id" in st.session_state:
            folder = f"temp_storage_{st.session_state['session_id']}"
            if os.path.exists(folder):
                shutil.rmtree(folder)
            del st.session_state["session_id"]
        st.rerun()

# --- File Upload Section ---
st.markdown("""
    <div class="upload-container">
        <h3 style="color: #000000; margin-bottom: 1rem;">📁 UPLOAD YOUR FILES</h3>
        <p style="color: #666666;">Drag and drop files or folders (ZIPs will be auto-extracted)</p>
    </div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "",
    accept_multiple_files=True,
    label_visibility="collapsed"
)

# --- Chunk Size Settings ---
st.markdown("""
    <div class="chunk-size-container">
        <div class="chunk-size-title">⚙️ CHUNK SIZE SETTINGS</div>
    </div>
""", unsafe_allow_html=True)

# Custom size input
col1, col2 = st.columns([1, 1])
with col1:
    custom_size = st.text_input(
        "Custom Size", 
        value="2MB", 
        placeholder="e.g., 2MB, 5MB, 10MB",
        help="Enter custom chunk size (e.g., 2MB, 5MB, 10MB)"
    )

# Predefined size buttons
st.markdown('<div class="size-buttons">', unsafe_allow_html=True)
size_options = ["2MB", "5MB", "7MB", "10MB", "15MB", "20MB"]
selected_size = st.session_state.get("selected_size", "2MB")

cols = st.columns(len(size_options))
for i, size in enumerate(size_options):
    with cols[i]:
        if st.button(size, key=f"size_{size}"):
            st.session_state["selected_size"] = size
            custom_size = size

st.markdown('</div>', unsafe_allow_html=True)

# Parse chunk size
try:
    max_chunk_size = humanfriendly.parse_size(custom_size)
    st.success(f"✅ Chunk size set to: **{humanfriendly.format_size(max_chunk_size)}**")
except:
    st.error("❌ Invalid size format. Use: 2MB, 5MB, etc.")
    max_chunk_size = 2 * 1024 * 1024

# --- Process Button ---
if uploaded_files:
    if st.button("🚀 PROCESS FILES", key="process_btn", type="primary"):
        with st.spinner("Processing files..."):
            if os.path.exists(BASE_TEMP_DIR):
                shutil.rmtree(BASE_TEMP_DIR)
            os.makedirs(INPUT_DIR, exist_ok=True)
            os.makedirs(OUTPUT_DIR, exist_ok=True)

            for uploaded_file in uploaded_files:
                file_path = os.path.join(INPUT_DIR, uploaded_file.name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if uploaded_file.name.endswith(".zip"):
                    try:
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(INPUT_DIR)
                        os.remove(file_path)
                    except zipfile.BadZipFile:
                        st.error(f"❌ {uploaded_file.name} is not a valid ZIP file.")

            results = split_folder_intelligently(INPUT_DIR, max_chunk_size, OUTPUT_DIR)
            st.session_state["zip_results"] = results

# --- Display Results ---
results = st.session_state.get("zip_results", [])

if results:
    st.markdown("""
        <div class="results-container">
            <h3 style="color: #000000; text-align: center; margin-bottom: 1rem;">✅ PROCESSING COMPLETE!</h3>
        </div>
    """, unsafe_allow_html=True)
    
    all_chunks = []

    for result in results:
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border: 1px solid #000000;">
                <h4 style="color: #000000; margin: 0;">📁 {result['original']}</h4>
                <p style="color: #666666; margin: 0.5rem 0;">Size: {humanfriendly.format_size(result['size'])}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Download buttons for each chunk
        cols = st.columns(min(len(result["chunks"]), 4))
        for i, chunk in enumerate(result["chunks"]):
            chunk_path = os.path.join(OUTPUT_DIR, chunk)
            all_chunks.append(chunk_path)
            with cols[i % 4]:
                with open(chunk_path, "rb") as f:
                    st.download_button(
                        label=f"📥 {chunk}",
                        data=f.read(),
                        file_name=chunk,
                        mime="application/zip",
                        key=f"download_{chunk}"
                    )

    # Download all as single ZIP
    st.markdown("---")
    all_zip_bytes = BytesIO()
    with zipfile.ZipFile(all_zip_bytes, 'w', zipfile.ZIP_DEFLATED) as allzip:
        for zip_path in all_chunks:
            allzip.write(zip_path, arcname=os.path.basename(zip_path))
    all_zip_bytes.seek(0)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.download_button(
            label="📦 DOWNLOAD ALL CHUNKS AS ZIP",
            data=all_zip_bytes,
            file_name="ALL_CHUNKS.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )
