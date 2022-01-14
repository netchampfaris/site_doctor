from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in site_doctor/__init__.py
from site_doctor import __version__ as version

setup(
	name="site_doctor",
	version=version,
	description="A tool to check the health of websites ",
	author="Faris",
	author_email="faris@frappe.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
