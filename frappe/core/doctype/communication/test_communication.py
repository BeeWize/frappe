# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import unittest
from urllib.parse import quote

import frappe
from frappe.email.doctype.email_queue.email_queue import EmailQueue
from frappe.core.doctype.communication.communication import get_emails

test_records = frappe.get_test_records('Communication')

class TestCommunication(unittest.TestCase):

	def test_email(self):
		valid_email_list = ["Full Name <full@example.com>",
		'"Full Name with quotes and <weird@chars.com>" <weird@example.com>',
		"Surname, Name <name.surname@domain.com>",
		"Purchase@ABC <purchase@abc.com>", "xyz@abc2.com <xyz@abc.com>",
		"Name [something else] <name@domain.com>"]

		invalid_email_list = ["[invalid!email]", "invalid-email",
		"tes2", "e", "rrrrrrrr", "manas","[[[sample]]]",
		"[invalid!email].com"]

		for x in valid_email_list:
			self.assertTrue(frappe.utils.parse_addr(x)[1])

		for x in invalid_email_list:
			self.assertFalse(frappe.utils.parse_addr(x)[0])

	def test_name(self):
		valid_email_list = ["Full Name <full@example.com>",
		'"Full Name with quotes and <weird@chars.com>" <weird@example.com>',
		"Surname, Name <name.surname@domain.com>",
		"Purchase@ABC <purchase@abc.com>", "xyz@abc2.com <xyz@abc.com>",
		"Name [something else] <name@domain.com>"]

		invalid_email_list = ["[invalid!email]", "invalid-email",
		"tes2", "e", "rrrrrrrr", "manas","[[[sample]]]",
		"[invalid!email].com"]

		for x in valid_email_list:
			self.assertTrue(frappe.utils.parse_addr(x)[0])

		for x in invalid_email_list:
			self.assertFalse(frappe.utils.parse_addr(x)[0])

	def test_circular_linking(self):
		a = frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"content": "This was created to test circular linking: Communication A",
		}).insert(ignore_permissions=True)

		b = frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"content": "This was created to test circular linking: Communication B",
			"reference_doctype": "Communication",
			"reference_name": a.name
		}).insert(ignore_permissions=True)

		c = frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"content": "This was created to test circular linking: Communication C",
			"reference_doctype": "Communication",
			"reference_name": b.name
		}).insert(ignore_permissions=True)

		a = frappe.get_doc("Communication", a.name)
		a.reference_doctype = "Communication"
		a.reference_name = c.name

		self.assertRaises(frappe.CircularLinkingError, a.save)

	def test_deduplication_timeline_links(self):
		frappe.delete_doc_if_exists("Note", "deduplication timeline links")

		note = frappe.get_doc({
			"doctype": "Note",
			"title": "deduplication timeline links",
			"content": "deduplication timeline links"
		}).insert(ignore_permissions=True)

		comm = frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"content": "Deduplication of Links",
			"communication_medium": "Email"
		}).insert(ignore_permissions=True)

		#adding same link twice
		comm.add_link(link_doctype="Note", link_name=note.name, autosave=True)
		comm.add_link(link_doctype="Note", link_name=note.name, autosave=True)

		comm = frappe.get_doc("Communication", comm.name)

		self.assertNotEqual(2, len(comm.timeline_links))

	def test_contacts_attached(self):
		contact_sender = frappe.get_doc({
			"doctype": "Contact",
			"first_name": "contact_sender",
		})
		contact_sender.add_email("comm_sender@example.com")
		contact_sender.insert(ignore_permissions=True)

		contact_recipient = frappe.get_doc({
			"doctype": "Contact",
			"first_name": "contact_recipient",
		})
		contact_recipient.add_email("comm_recipient@example.com")
		contact_recipient.insert(ignore_permissions=True)

		contact_cc = frappe.get_doc({
			"doctype": "Contact",
			"first_name": "contact_cc",
		})
		contact_cc.add_email("comm_cc@example.com")
		contact_cc.insert(ignore_permissions=True)

		comm = frappe.get_doc({
			"doctype": "Communication",
			"communication_medium": "Email",
			"subject": "Contacts Attached Test",
			"sender": "comm_sender@example.com",
			"recipients": "comm_recipient@example.com",
			"cc": "comm_cc@example.com"
		}).insert(ignore_permissions=True)

		comm = frappe.get_doc("Communication", comm.name)

		contact_links = []
		for timeline_link in comm.timeline_links:
			contact_links.append(timeline_link.link_name)

		self.assertIn(contact_sender.name, contact_links)
		self.assertIn(contact_recipient.name, contact_links)
		self.assertIn(contact_cc.name, contact_links)

	def test_get_communication_data(self):
		from frappe.desk.form.load import get_communication_data

		frappe.delete_doc_if_exists("Note", "get communication data")

		note = frappe.get_doc({
			"doctype": "Note",
			"title": "get communication data",
			"content": "get communication data"
		}).insert(ignore_permissions=True)

		comm_note_1 = frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"content": "Test Get Communication Data 1",
			"communication_medium": "Email"
		}).insert(ignore_permissions=True)

		comm_note_1.add_link(link_doctype="Note", link_name=note.name, autosave=True)

		comm_note_2 = frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"content": "Test Get Communication Data 2",
			"communication_medium": "Email"
		}).insert(ignore_permissions=True)

		comm_note_2.add_link(link_doctype="Note", link_name=note.name, autosave=True)

		comms = get_communication_data("Note", note.name, as_dict=True)

		data = []
		for comm in comms:
			data.append(comm.name)

		self.assertIn(comm_note_1.name, data)
		self.assertIn(comm_note_2.name, data)

	def test_link_in_email(self):
		frappe.delete_doc_if_exists("Note", "test document link in email")

		create_email_account()

		note = frappe.get_doc({
			"doctype": "Note",
			"title": "test document link in email",
			"content": "test document link in email"
		}).insert(ignore_permissions=True)

		comm = frappe.get_doc({
			"doctype": "Communication",
			"communication_medium": "Email",
			"subject": "Document Link in Email",
			"sender": "comm_sender@example.com",
			"recipients": "comm_recipient+{0}+{1}@example.com".format(quote("Note"), quote(note.name)),
		}).insert(ignore_permissions=True)

		doc_links = []
		for timeline_link in comm.timeline_links:
			doc_links.append((timeline_link.link_doctype, timeline_link.link_name))

		self.assertIn(("Note", note.name), doc_links)

	def parse_emails(self):
		emails = get_emails(
			[
				'comm_recipient+DocType+DocName@example.com',
				'"First, LastName" <first.lastname@email.com>',
				'test@user.com'
			]
		)

		self.assertEqual(emails[0], "comm_recipient+DocType+DocName@example.com")
		self.assertEqual(emails[1], "first.lastname@email.com")
		self.assertEqual(emails[2], "test@user.com")

class TestCommunicationEmailMixin(unittest.TestCase):
	def new_communication(self, recipients=None, cc=None, bcc=None):
		recipients = ', '.join(recipients or [])
		cc = ', '.join(cc or [])
		bcc = ', '.join(bcc or [])

		comm = frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"content": "Test content",
			"recipients": recipients,
			"cc": cc,
			"bcc": bcc
		}).insert(ignore_permissions=True)
		return comm

	def new_user(self, email, **user_data):
		user_data.setdefault('first_name', 'first_name')
		user = frappe.new_doc('User')
		user.email = email
		user.update(user_data)
		user.insert(ignore_permissions=True, ignore_if_duplicate=True)
		return user

	def test_recipients(self):
		to_list = ['to@test.com', 'receiver <to+1@test.com>', 'to@test.com']
		comm = self.new_communication(recipients = to_list)
		res = comm.get_mail_recipients_with_displayname()
		self.assertCountEqual(res, ['to@test.com', 'receiver <to+1@test.com>'])
		comm.delete()

	def test_cc(self):
		to_list = ['to@test.com']
		cc_list = ['cc+1@test.com', 'cc <cc+2@test.com>', 'to@test.com']
		user = self.new_user(email='cc+1@test.com', thread_notify=0)
		comm = self.new_communication(recipients=to_list, cc=cc_list)
		res = comm.get_mail_cc_with_displayname()
		self.assertCountEqual(res, ['cc <cc+2@test.com>'])
		user.delete()
		comm.delete()

	def test_bcc(self):
		bcc_list = ['bcc+1@test.com', 'cc <bcc+2@test.com>', ]
		user = self.new_user(email='bcc+2@test.com', enabled=0)
		comm = self.new_communication(bcc=bcc_list)
		res = comm.get_mail_bcc_with_displayname()
		self.assertCountEqual(res, ['bcc+1@test.com'])
		user.delete()
		comm.delete()

	def test_sendmail(self):
		to_list = ['to <to@test.com>']
		cc_list = ['cc <cc+1@test.com>', 'cc <cc+2@test.com>']

		comm = self.new_communication(recipients=to_list, cc=cc_list)
		comm.send_email()
		doc = EmailQueue.find_one_by_filters(communication=comm.name)
		mail_receivers = [each.recipient for each in doc.recipients]
		self.assertIsNotNone(doc)
		self.assertCountEqual(to_list+cc_list, mail_receivers)
		doc.delete()
		comm.delete()

def create_email_account():
	frappe.delete_doc_if_exists("Email Account", "_Test Comm Account 1")

	frappe.flags.mute_emails = False
	frappe.flags.sent_mail = None

	email_account = frappe.get_doc({
		"is_default": 1,
		"is_global": 1,
		"doctype": "Email Account",
		"domain":"example.com",
		"append_to": "ToDo",
		"email_account_name": "_Test Comm Account 1",
		"enable_outgoing": 1,
		"smtp_server": "test.example.com",
		"email_id": "test_comm@example.com",
		"password": "password",
		"add_signature": 1,
		"signature": "\nBest Wishes\nTest Signature",
		"enable_auto_reply": 1,
		"auto_reply_message": "",
		"enable_incoming": 1,
		"notify_if_unreplied": 1,
		"unreplied_for_mins": 20,
		"send_notification_to": "test_comm@example.com",
		"pop3_server": "pop.test.example.com",
		"imap_folder": [{"folder_name": "INBOX", "append_to": "ToDo"}],
		"no_remaining":"0",
		"enable_automatic_linking": 1
	}).insert(ignore_permissions=True)

	return email_account
