from setuptools import setup, find_packages

setup(
    name="jp-recruit-extractor",
    version="0.1.0",
    description="日本招聘案件データ抽出システム — AI-guided, rule-powered extraction pipeline",
    author="Your Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0",
        "python-dotenv>=1.0",
        "PyMuPDF>=1.23",
        "python-docx>=1.0",
        "openpyxl>=3.1",
        "beautifulsoup4>=4.12",
        "lxml>=4.9",
        "anthropic>=0.30",
        "openai>=1.0",
        "fastapi>=0.104",
        "uvicorn[standard]>=0.24",
        "typer>=0.9",
        "rich>=13.0",
        "structlog>=23.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4",
            "pytest-cov>=4.1",
            "httpx>=0.25",
        ],
        "ml": [
            "scikit-learn>=1.3",
            "spacy>=3.7",
        ],
        "ocr": [
            "pytesseract>=0.3",
            "Pillow>=10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "jp-extract=src.cli:app",
        ],
    },
)
