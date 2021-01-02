import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="paperstorage", # Replace with your own username
    version="1.0.0",
    author="Florian Eder",
    author_email="others.meder@gmail.com",
    description="A module to create paper backups for arbitrary data that are recoverable by simple means",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/schroeding/paperstorage",
    packages='paperstorage',
    classifiers=[
		"Development Status :: 5 - Production/Stable"
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)