# Copyright (c) 2022, Faris and contributors
# For license information, please see license.txt

import frappe
import requests
from bs4 import BeautifulSoup, SoupStrainer
from frappe.model.document import Document
from urllib.parse import urlparse, urljoin


class SiteScan(Document):
	def before_insert(self):
		self.validate_url()

	def after_insert(self):
		frappe.enqueue(
			"site_doctor.site_doctor.doctype.site_scan.site_scan.run_scan",
			name=self.name,
			queue="short",
			timeout=1 * 60 * 60,  # 1 hour
			at_front=True,
			now=self.status == "Now",
		)

	def validate_url(self):
		try:
			res = requests.get(self.url)
			res.raise_for_status()
		except requests.HTTPError:
			frappe.throw(f'Inaccessible web page: "{self.url}"')

		print(res.headers)

		if "text/html" not in res.headers["Content-Type"]:
			frappe.throw(f'Invalid web page: "{self.url}"')

	def start(self):
		self.started_at = frappe.utils.now()
		self.status = "Running"
		self.save()
		frappe.db.commit()
		self.publish_update()
		try:
			self.find_broken_links()
		except Exception:
			self.status = "Errored"
			error = f"<div><pre>{frappe.utils.get_traceback()}</pre></div>"
			self.add_comment("Comment", f"Error while scanning site: <br>{error}")

		if not self.status == "Errored":
			self.completed_at = frappe.utils.now()
			self.execution_time = frappe.utils.time_diff_in_seconds(
				self.completed_at, self.started_at
			)
			self.status = "Completed"
		self.save()
		self.publish_update("success")

	def find_broken_links(self):
		self.processed_links = {}
		self.processed_pages = {}
		self.linked_pages = []
		self.find_broken_links_in_page(self.url)

	def find_broken_links_in_page(self, page_url):
		if page_url.endswith("/"):
			page_url = page_url[:-1]

		if page_url in self.processed_pages:
			return

		linked_pages = []

		print("processing", page_url)
		frappe.publish_realtime(
			"site_scan_page", {"page": page_url, "name": self.name}, user=frappe.session.user
		)

		res = requests.get(page_url)
		res.raise_for_status()
		if "text/html" not in res.headers["Content-Type"]:
			return

		hostname = urlparse(self.url).scheme + "://" + urlparse(self.url).netloc
		html = res.text
		soup = BeautifulSoup(html, "html.parser", parse_only=SoupStrainer("a"))
		for link in soup.find_all("a"):
			link_url = link.get("href")

			if (
				not link_url
				or link_url in ["/", "#"]
				or link_url.startswith(("mailto:", "tel:", "skype:", "#"))
			):
				continue

			print("checking", link_url)

			if not link_url.startswith("http"):
				link_url = urljoin(hostname, link_url)

			if link_url.endswith("/"):
				link_url = link_url[:-1]

			# skip if url is processed and is not broken
			if link_url in self.processed_links and self.processed_links[link_url]:
				continue

			success = True
			res = None
			status_code = None
			try:
				res = requests.head(link_url, verify=True, timeout=10)
				status_code = res.status_code
				broken = status_code >= 400
				success = not broken
			except requests.exceptions.RequestException as e:
				if e.response:
					status_code = e.response.status_code
				success = False

			if not success:
				self.append(
					"broken_links",
					{
						"page_url": page_url,
						"link": link_url,
						"link_text": link.text.strip(),
						"source": str(link),
						"response_status_code": status_code,
					},
				)
				self.publish_update()
			else:
				if link_url.startswith(hostname):
					linked_pages.append(link_url)

			self.processed_links[link_url] = success

		self.processed_pages[page_url] = True

		for url in linked_pages:
			try:
				self.find_broken_links_in_page(url)
			except requests.HTTPError:
				pass

	def publish_update(self, type=None):
		if type == "success":
			frappe.publish_realtime(
				"site_scan_complete", {"name": self.name}, user=frappe.session.user
			)
		frappe.publish_realtime(
			"site_scan_progress", {"doc": self.as_dict()}, user=frappe.session.user
		)


def run_scan(name):
	doc = frappe.get_doc("Site Scan", name)
	doc.start()