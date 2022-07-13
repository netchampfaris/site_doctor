# Copyright (c) 2022, Faris and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests

class Site(Document):
	def validate(self):
		if not self.url.startswith("https"):
			self.url = "https://" + self.url
		self.name = self.url
		requests.head(self.url)

	def scan_site(self):
		scan = frappe.get_doc(doctype='Site Scan', site=self.name, status='Running').insert()
		scan.reload()
		scan.start()
		return scan

@frappe.whitelist()
def scan_site(doc=None):
	doc = frappe.parse_json(doc)
	site = frappe.get_doc('Site', doc.name)
	scan = site.scan_site()
	link = frappe.utils.get_link_to_form('Site Scan', scan.name)
	frappe.msgprint(frappe._("Scan completed at {0}").format(link))