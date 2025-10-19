"""
File Server Core Setup Configuration
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
    "loguru>=0.7.0",
    "minio>=7.1.0",
    "asyncpg>=0.28.0",
    "pdfplumber>=0.9.0",
    "aiofiles>=23.0.0",
    "tenacity>=8.2.0",
    "PyYAML>=6.0",
    "python-multipart>=0.0.6",
    "mistralai>=1.0.0",  # For OCR functionality
    "python-dotenv>=1.0.0",  # For environment configuration
]

dev_requirements = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.7.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
]

setup(
    name="file-server-core",
    version="0.1.0",
    author="File Server Team",
    author_email="team@example.com",
    description="文档处理与知识库管理核心库",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/file-server-core",
    packages=find_packages(include=["file_server_core", "file_server_core.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: General",
        "Topic :: Database",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "all": requirements + dev_requirements,
    },
    include_package_data=True,
    package_data={
        "file_server_core": ["py.typed"],
    },
    entry_points={
        "console_scripts": [
            "file-server-core=file_server_core.cli:main",
        ],
    },
    keywords="document processing, OCR, knowledge base, file server, vector database",
    project_urls={
        "Bug Reports": "https://github.com/your-org/file-server-core/issues",
        "Source": "https://github.com/your-org/file-server-core",
        "Documentation": "https://file-server-core.readthedocs.io/",
    },
)