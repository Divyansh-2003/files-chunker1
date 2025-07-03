import streamlit as st
import os
import zipfile
import shutil
from pathlib import Path
import tempfile
import humanfriendly
from io import BytesIO

st.set_page_config(page_title="Smart Folder Chunker", layout="centered", initial_sidebar_state="auto")
st.markdown("""
    <style>
        html, body, [class*="css"]  {
            background: linear-gradient(180deg, #f5f0fa 15%, #ffffff 100%) !important;
            font-family: 'Nunito', sans-serif;
            color: #2d2d2d;
        }
        .main > div {
            max-width: 85%;
            margin: auto;
        }
        h1 {
            font-size: 2.8em !important;
            font-weight: 800 !important;
            margin-top: 0.2em;
        }
        .stButton button {
            border-radius: 6px;
            padding: 0.6em 1.4em;
            border: 1px solid #a3a3a3;
            background-color: #f3f3f3;
            font-weight: 600;
            color: #2d2d2d;
        }
        .stDownloadButton button {
            border-radius: 6px;
            padding: 0.6em 1.4em;
            font-weight: 600;
            background-color: #f3f3f3;
            color: #2d2d2d;
            border: 1px solid #a3a3a3;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Smart Folder Chunker")
st.write("Upload folders or ZIPs. Files will be chunked and zipped intelligently while preserving folder structure.")

if st.button("Reset Session"):
    st.experimental_rerun()

# File upload
uploaded_files = st.file_uploader(
    "Upload files or folders (ZIPs will be auto-extracted)",
    accept_multiple_files=True,
    type=None
)

# Chunk size controls (moved below upload)
st.markdown("**Max Chunk Size**")
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
chunk_size_option = col1.radio("", ["Custom"], label_visibility="collapsed")
custom_size = col5.text_input("", "2MB", label_visibility="collapsed")

quick_sizes = {"3MB": 3, "5MB": 5, "7MB": 7, "10MB": 10}
for i, (label, size) in enumerate(quick_sizes.items()):
    col = [col2, col3, col4, col5][i]
    if col.button(label):
        custom_size = label

try:
    max_chunk_size = humanfriendly.parse_size(custom_size)
except:
    st.error("Invalid chunk size. Use formats like 2MB, 5MB, etc.")
    max_chunk_size = 2 * 1024 * 1024

# Helper functions
def get_folder_size(folder_path):
    total = 0
    for dirpath, _, filenames in os.walk(folder_path):
        for filename in filenames:
            total += os.path.getsize(os.path.join(dirpath, filename))
    return total

def create_zip_from_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in Path(folder_path).rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(folder_path.parent)
                zipf.write(file_path, arcname)

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
            results.append({
                'original': folder_name,
                'chunks': [zip_name],
                'size': folder_size
            })
        else:
            parts = split_large_folder(subfolder, folder_name, max_chunk_size, output_dir)
            results.append({
                'original': folder_name,
                'chunks': parts,
                'size': folder_size
            })
    return results

if uploaded_files and st.button("Process Files"):
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = os.path.join(temp_dir, "input")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(input_dir, exist_ok=True)

        for uploaded_file in uploaded_files:
            file_path = os.path.join(input_dir, uploaded_file.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # If it's a zip, unzip it
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(input_dir)
                os.remove(file_path)

        st.write("🔧 Processing files...")
        results = split_folder_intelligently(input_dir, max_chunk_size, output_dir)
        st.success("✅ Processing complete!")

        for result in results:
            folder_col1, folder_col2 = st.columns([3, 1])
            with folder_col1:
                st.markdown(f"📁 **{result['original']}** ({humanfriendly.format_size(result['size'])})")
            with folder_col2:
                zip_all = BytesIO()
                with zipfile.ZipFile(zip_all, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for chunk in result['chunks']:
                        with open(os.path.join(output_dir, chunk), 'rb') as f:
                            zipf.writestr(chunk, f.read())
                zip_all.seek(0)
                st.download_button("Download All as ZIP", zip_all, file_name=f"{result['original']}_all_chunks.zip")

            for chunk in result['chunks']:
                chunk_path = os.path.join(output_dir, chunk)
                if os.path.exists(chunk_path):
                    with open(chunk_path, "rb") as f:
                        st.download_button(
                            label=f"📥 Download {chunk}",
                            data=f.read(),
                            file_name=chunk,
                            mime="application/zip"
                        )
