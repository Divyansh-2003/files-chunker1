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

# --- Custom CSS for Updated Theme ---
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #b9b6c1; /* Change background to #b9b6c1 */
    }
    
    /* Header container */
    .header-container {
        display: flex;
        justify-content: space-between; /* Align logo and reset button */
        align-items: center;
        padding: 1rem 0;
        margin-bottom: 2rem;
    }
    
    /* Logo styling */
    .logo {
        font-size: 2rem; /* Slightly smaller font size */
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
        padding: 8px 16px;
        font-size: 14px;
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
    
    /* Upload area styling */
    .upload-container {
        background-color: #ffffff;
        padding: 0.5rem; /* Reduce padding */
        border-radius: 12px;
        border: 2px dashed #000000;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Upload text styling */
    .upload-text {
        font-size: 0.9rem; /* Reduce font size */
        color: #000000;
        margin-bottom: 0;
    }
    
    /* Chunk size container */
    .chunk-size-container {
        display: flex; /* Align chunk size settings in one line */
        gap: 10px;
        justify-content: center;
        align-items: center;
        margin: 1rem 0;
        flex-wrap: wrap; /* Allow wrapping for smaller screens */
    }
    
    .chunk-size-title {
        font-size: 1rem; /* Adjust font size */
        font-weight: bold;
        color: #000000;
        margin-right: 1rem;
    }
    
    /* Predefined buttons */
    .size-buttons {
        display: flex;
        gap: 10px;
        justify-content: center;
        flex-wrap: nowrap; /* Keep buttons in the same row */
    }
    
    .size-btn {
        background-color: #ffffff;
        border: 2px solid #000000;
        border-radius: 8px;
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
    
    /* Process button */
    .process-btn {
        background-color: #000000;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        font-size: 14px; /* Smaller font size */
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
        padding: 0.75rem; /* Reduce padding */
        border-radius: 12px;
        border: 2px solid #000000;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Processing complete text */
    .processing-complete {
        font-size: 1rem; /* Reduce font size */
        color: #000000;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    /* Result item styling */
    .result-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #f8f9fa;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #000000;
        font-size: 0.9rem; /* Smaller font size */
    }
    
    /* Hide Streamlit elements */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
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
    </div>
""", unsafe_allow_html=True)

# Add JavaScript for reset functionality
st.markdown("""
    <script>
    function resetApp() {
        localStorage.clear();
        sessionStorage.clear();
        window.location.reload(true);
    }
    </script>
""", unsafe_allow_html=True)

# --- Center Reset Button ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Reset Session", key="reset_btn", type="secondary"):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Clear temp directories
        if os.path.exists(BASE_TEMP_DIR):
            shutil.rmtree(BASE_TEMP_DIR)
        
        # Recreate directories
        os.makedirs(INPUT_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Reset uploaded files
        st.session_state["uploaded_files"] = None
        st.session_state["zip_results"] = None
        
        # Force page refresh
        st.rerun()

# --- File Upload Section ---
st.markdown("""
    <div class="upload-container">
        <p class="upload-text">📁 UPLOAD YOUR FILES - Drag and drop files or folders (ZIPs will be auto-extracted)</p>
    </div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "",
    accept_multiple_files=True,
    label_visibility="collapsed"
)

# --- Chunk Size Settings ---
if 'selected_chunk_size' not in st.session_state:
    st.session_state.selected_chunk_size = "2MB"

# Update the chunk size container HTML
st.markdown("""
    <div class="chunk-size-container">
        <div class="chunk-size-title">⚙️ CHUNK SIZE SETTINGS</div>
        <input type="text" id="custom-size" placeholder="e.g., 2MB, 5MB, 10MB" 
               style="border: 2px solid #000000; border-radius: 8px; font-weight: bold; color: #000000; background-color: #ffffff;">
        <div class="size-buttons">
            <button class="size-btn" onclick="selectSize('2MB')">2MB</button>
            <button class="size-btn" onclick="selectSize('5MB')">5MB</button>
            <button class="size-btn" onclick="selectSize('7MB')">7MB</button>
            <button class="size-btn" onclick="selectSize('10MB')">10MB</button>
        </div>
    </div>
""", unsafe_allow_html=True)

# Add JavaScript for handling chunk size selection
st.markdown("""
    <script>
    function selectSize(size) {
        const buttons = document.querySelectorAll('.size-btn');
        buttons.forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById('custom-size').value = size;
        updateChunkSize(size);
    }

    function updateChunkSize(size) {
        const args = {size: size};
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: size
        }, '*');
    }
    </script>
""", unsafe_allow_html=True)

# Handle chunk size changes
custom_size = st.text_input("Enter custom chunk size (e.g., 2MB, 5MB, 10MB):", value=st.session_state.selected_chunk_size)
if custom_size:
    try:
        max_chunk_size = humanfriendly.parse_size(custom_size)
        st.session_state.selected_chunk_size = custom_size
        st.success(f"✅ Chunk size set to: **{humanfriendly.format_size(max_chunk_size)}**")
    except:
        st.error("❌ Invalid size format. Use: 2MB, 5MB, etc.")

# --- Process Button ---
if uploaded_files:
    if st.button("🚀 PROCESS FILES", key="process_btn", type="primary"):
        with st.spinner("Processing files..."):
            # Get the current selected chunk size
            try:
                max_chunk_size = humanfriendly.parse_size(st.session_state.selected_chunk_size)
            except:
                max_chunk_size = 2 * 1024 * 1024  # Default to 2MB if parsing fails
                
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
            <p class="processing-complete">✅ PROCESSING COMPLETE!</p>
        </div>
    """, unsafe_allow_html=True)
    
    all_chunks = []

    for result in results:
        st.markdown(f"""
            <div class="result-item">
                <span>📁 {result['original']}</span>
                <span>Size: {humanfriendly.format_size(result['size'])}</span>
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
