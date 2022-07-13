// Copyright (c) 2022, Faris and contributors
// For license information, please see license.txt

frappe.ui.form.on("Site Scan", {
	// refresh: function(frm) {

	// }
	setup(frm) {
		frappe.realtime.on("site_scan_progress", function (data) {
			console.log(data.doc);
			if (data.doc) {
				if (data.doc.status == "Running") {
					frm.page.set_indicator(__("Running"), "orange");
				}
				frappe.model.sync(data.doc);
				frm.refresh();
				// frm.set_value(data.doc);
			}
		});
		frappe.realtime.on("site_scan_complete", function (data) {
			if (data.name && frm.doc.name === data.name) {
				frm.reload_doc();
			}
		});
		frappe.realtime.on("site_scan_page", (data) => {
			if (data.name === frm.doc.name && data.page) {
				frm.dashboard.clear_headline();
				frm.dashboard.set_headline(`Scanning ${data.page}`);
			}
		});
	},
});
