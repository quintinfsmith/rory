import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rory",
    version="0.2.0",
    description="Play along to MIDI files in console",
    author="Quintin Smith",
    author_email="smith.quintin@protonmail.com",
    install_requires=['pyinotify', 'wrecked', 'apres'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/quintinfsmith/rory",
    python_requires=">=3.6",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: POSIX :: Linux",
    ]
)
