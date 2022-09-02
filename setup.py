import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="makelove",
    version="0.0.10",
    author="Joel Schumacher",
    author_email="joelschum@gmail.com",
    description="A packaging tool for [löve](https://love2d.org) games",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pfirsich/makelove",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=["Pillow>=7.0", "appdirs>=1.4.3", "toml>=0.10"],
    entry_points={
        "console_scripts": ["makelove=makelove.makelove:main"],
    },
)
