import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
	long_description = fh.read()

setuptools.setup(
	name="paperstorage", # Replace with your own username
	version="0.9.0",
	author="Florian Eder",
	author_email="others.meder@gmail.com",
	description="A module to create paper backups for arbitrary data that are recoverable by simple means",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/schroeding/paperstorage",
	packages='paperstorage',
	classifiers=[
		"Development Status :: 4 - Beta",
		"Programming Language :: Python :: 3",
		"Intended Audience :: System Administrators",
		"Intended Audience :: End Users/Desktop",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
		"Operating System :: OS Independent",
		"Topic :: System :: Archiving :: Backup",
		"Topic :: Printing"
	],
	python_requires='>=3.6',
)