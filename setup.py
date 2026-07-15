from setuptools import setup, find_packages

setup(
    name="theoldllm",
    version="0.1.0",
    description="Python client for TheOldLLM - Free Multi-Model AI Chat API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="TheOldLLM Community",
    url="https://github.com/yourusername/theoldllm-python",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        "async": ["httpx>=0.27.0"],
        "proxy": ["aiohttp>=3.9.0", "playwright>=1.40.0"],
    },
    entry_points={
        "console_scripts": [
            "theoldllm-proxy=theoldllm.proxy_server:main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
