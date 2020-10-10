import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="speedy researcher", # Replace with your own username
    version="0.0.1",
    author="Tobias Renwick",
    author_email="renwick@ualberta.ca",
    description="A AI managed speed reading application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/qubies/speedy_researcher",
    packages=setuptools.find_packages(),
    install_requires=[
        'pyqt5',
        'textract',
        'pynput',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    include_package_data=True, 
)
