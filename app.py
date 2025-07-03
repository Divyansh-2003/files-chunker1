# smart_folder_chunker_ui.py
import streamlit as st
import os
import zipfile
import shutil
from pathlib import Path
import tempfile
import humanfriendly

st.set_page_config(layout="wide", page_title="Smart Folder Chunker")

# Custom CSS for Slack-inspired UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Nunito', sans-serif;
        background-color: #f8f9fa;
        color: #1d1c1d;
    }
    .title-text {
        font-size: 3em;
        font-weight: bold;
        font-family: 'Nunito', sans-serif;
        color: #1264a3;
        margin-bottom: 0.5em;
    }
    .button-main, .button-reset {
        border-radius: 8px;
        padding: 0.5rem 1.2rem;
        font-size: 1rem;
        font-weight: bold;
        background-color: #1264a3;
        color: white;
        border: none;
    }
    .button-reset {
        background-color: #e01e5a;
    }
    .stButton > button {
        width: auto !important;
    }
    .drag-drop-area .css-1b0udgb {
        padding: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# App title section
col1, col2 = st.columns([8, 1])
with col1:
    st.markdown("<div class='title-text'>SMART FOLDER CHUNKER</div>", unsafe_allow_html=True)
with col2:
    if st.button("Reset Session", key="reset", help="Clear all uploaded and processed files"):
        st.session_state.clear()
        st.experimental_rerun()

# Sidebar settings
with st.sidebar:
    st.subheader("Max chunk size")
    size_options = ["3MB", "5MB", "7MB", "10MB"]
    custom_size = st.text_input("Custom", value="1MB")
    selected_size = custom_size
    for size in size_options:
        if st.button(size):
            selected_size = size

    try:
        max_chunk_size = humanfriendly.parse_size(selected_size)
        st.success(f"Chunk size: {humanfriendly.format_size(max_chunk_size)}")
    except:
        max_chunk_size = 1 * 1024 * 1024
        st.error("Invalid size format. Use: 1MB, 5MB, etc.")

st.markdown("""---""")

st.markdown("<h5>Upload folders or ZIPs. Files will be chunked and zipped intelligently while preserving folder structure.</h5>", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Upload files or folders (ZIPs will be auto-extracted)",
    accept_multiple_files=True,
    type=None,
    label_visibility="collapsed"
)

process_col1, process_col2 = st.columns([2, 8])
process_trigger = process_col1.button("Process Files", key="process_files")

if process_trigger and uploaded_files:
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = os.path.join(temp_dir, "input")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(input_dir, exist_ok=True)

        for uploaded_file in uploaded_files:
            file_path = os.path.join(input_dir, uploaded_file.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(input_dir)
                os.remove(file_path)

        def get_folder_size(folder_path):
            return sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, filenames in os.walk(folder_path) for f in filenames)

        def create_zip_from_files(files, zip_path, base_folder):
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    arcname = file_path.relative_to(base_folder.parent)
                    zipf.write(file_path, arcname)

        def split_large_folder(folder_path, folder_name, max_size, output_dir):
            files = list(folder_path.rglob('*'))
            files = [f for f in files if f.is_file()]

            chunks = []
            current_chunk = []
            current_size = 0
            part_num = 1

            for file in files:
                file_size = os.path.getsize(file)
                if current_size + file_size > max_size and current_chunk:
                    zip_name = f"{folder_name}_part{part_num}.zip"
                    zip_path = os.path.join(output_dir, zip_name)
                    create_zip_from_files(current_chunk, zip_path, folder_path)
                    chunks.append(zip_name)
                    current_chunk = []
                    current_size = 0
                    part_num += 1

                current_chunk.append(file)
                current_size += file_size

            if current_chunk:
                zip_name = f"{folder_name}_part{part_num}.zip"
                zip_path = os.path.join(output_dir, zip_name)
                create_zip_from_files(current_chunk, zip_path, folder_path)
                chunks.append(zip_name)

            return chunks

        def create_zip_from_folder(folder_path, zip_path):
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(folder_path.parent)
                        zipf.write(file_path, arcname)

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

        st.info("\U0001F4C1 Processing files...")
        results = split_folder_intelligently(input_dir, max_chunk_size, output_dir)
        st.success("\u2705 Processing complete!")

        for result in results:
            folder_col, zip_col = st.columns([3, 1])
            with folder_col:
                st.markdown(f"<h6>\U0001F4C2 {result['original']} ({humanfriendly.format_size(result['size'])})</h6>", unsafe_allow_html=True)
            with zip_col:
                zip_all_path = os.path.join(output_dir, f"{result['original']}_ALL.zip")
                with zipfile.ZipFile(zip_all_path, 'w', zipfile.ZIP_DEFLATED) as bundle:
                    for zipname in result['chunks']:
                        bundle.write(os.path.join(output_dir, zipname), arcname=zipname)
                with open(zip_all_path, "rb") as zf:
                    st.download_button(
                        label=f"Download All as ZIP",
                        data=zf,
                        file_name=f"{result['original']}_ALL.zip",
                        mime="application/zip"
                    )

            for chunk in result['chunks']:
                chunk_path = os.path.join(output_dir, chunk)
                with open(chunk_path, "rb") as f:
                    st.download_button(
                        label=f"📥 Download {chunk}",
                        data=f.read(),
                        file_name=chunk,
                        mime="application/zip"
                    )

