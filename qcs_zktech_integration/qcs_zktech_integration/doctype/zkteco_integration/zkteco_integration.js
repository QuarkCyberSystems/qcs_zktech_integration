// Copyright (c) 2024, Quark Cyber Systems FZC and contributors
// For license information, please see license.txt

frappe.ui.form.on("ZKTeco Integration", {
	before_save(frm) {
        frm.set_value('from_date', '')
        frm.set_value('to_date', '')
	},
    fetch_transactions(frm) {
        frappe.call({
            method: "qcs_zktech_integration.qcs_zktech_integration.doctype.zkteco_integration.zkteco_integration.get_transactions",
            args: {
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
            },
            callback: function(r) {
                frappe.show_alert({
                    message:__('Sync Successful'),
                    indicator:'green'
                }, 5)
            }
        });
	},
});
