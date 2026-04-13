from setuptools import setup, find_packages

setup(
    name="ai-vibe-check",
    version="0.1.0",
    description="AI focus group for content creators. 80 simulated personas score your posts before you publish.",
    author="Anmol Gupta",
    url="https://github.com/anmolgupta824/ai-vibe-check",
    packages=find_packages(),
    install_requires=[
        "litellm>=1.30.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "vibe-check=vibe_check.cli:main",
        ],
    },
    python_requires=">=3.10",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Testing",
    ],
)
