
### Instructions to Run AWS Blog PDF Scraper

This script fetches AWS blog posts and saves them in HTML and PDF formats. Follow these steps to set it up for macOS, Linux, and Windows.

#### Prerequisites

1. **Python ≥ 3.11**: Ensure you have Python installed.
2. **Poetry**: For dependency management. Install it with:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

#### 1. Clone or Download the Script
Download or place this script in a folder of your choice.

#### 2. Install Dependencies Using Poetry
Inside the folder containing the script:
```bash
poetry install
```

#### 3. Install WeasyPrint Libraries
WeasyPrint requires additional system libraries depending on your OS. Follow the steps below for your platform:

---

#### WeasyPrint Installation

**Linux**  
For most Linux distributions, you can use the package manager:
```bash
# Debian/Ubuntu
sudo apt install python3-pip libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libffi-dev libjpeg-dev libopenjp2-7-dev

# Fedora
sudo dnf install python3-pip pango gcc python3-devel gcc-c++ zlib-devel libjpeg-devel openjpeg2-devel libffi-devel
```

**macOS**  
On macOS, install WeasyPrint libraries via Homebrew:
```bash
brew install pygobject3 pango cairo gdk-pixbuf libffi
```

After installing, set up the environment for library paths:
```bash
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH"
```

**Windows**  
1. **Install Python** from the [Microsoft Store](https://apps.microsoft.com/store/detail/python-39/9P7QFQMJRFP7).
2. **Install MSYS2** and required libraries:
   - Download and install [MSYS2](https://www.msys2.org/).
   - Open the MSYS2 shell and install Pango:
     ```bash
     pacman -S mingw-w64-x86_64-pango
     ```
3. **Install WeasyPrint in a virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate.bat
   python -m pip install weasyprint
   ```

---

#### 4. Activate the Poetry Environment and Run the Script

1. **Activate Poetry Shell**:
   ```bash
   poetry shell
   ```

2. **Run the Script**:
   ```bash
   python blog.py
   ```

#### Notes
- **Output**: HTML and PDF files will be saved in the `html_blogs` and `pdf_blog` directories, respectively.
- **Troubleshooting WeasyPrint**: If you encounter errors with libraries, refer to [WeasyPrint documentation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).