import smtplib, ssl
import argparse
import pandas as pd
import os
from glob import glob
from smtpd import DebuggingServer
import asyncore
import threading
from time import sleep
from email.message import EmailMessage
import mimetypes
from email.utils import make_msgid
from string import Template
from tqdm import tqdm
import sys
import subprocess as sp

# Grab the terminal size for printing
try:
    _, COLUMNS = sp.check_output(['stty', 'size']).decode().split()
# If pytest has capturing enabled or this is run without a tty, catch the exception
except sp.CalledProcessError:
    _, COLUMNS = 0, 0

def get_args(cmd):
	"""
	Parse args for the email merge script.
	"""
	parser = argparse.ArgumentParser(description="Mail merge python script. Email body files should include Python template fields that match the headers of the CSV files. For example, a column 'data1' in the CSV file should have a correspoding ${data1} in the template. Note that all spaces in CSV headers are replaced with underscores, and all characters are put in lower case, so 'Data 1' becomes '${data_1}'.", add_help=False)
	
	# So we can collect args from plugins. Geneva style
	parser.add_argument('-h', '--help', action='store_true', default=False, help='print this help message and exit')
	plugin_options = [path.split("/")[1].split(".")[0] for path in glob("plugins/*.py")]
	parser.add_argument("--plugin", action="store", help="Python plugin for extra data processing. Python files should be in plugins/. See README.md for details", choices=plugin_options)
	
	parser.add_argument("--html", action="store", help="HTML version of the email body. Images should be included with <img> tags with src='cid:${img0}', with increasing integers for each image.")
	parser.add_argument("--text", action="store", help="Plain text version of the email body")
	parser.add_argument("--img", action="store", nargs="+", default=[], help="Images to be included in the email body. Images should be listed in the order they appear in the HTML file.")
	parser.add_argument("--sent-from", action="store", help="Name to show as email sender")
	parser.add_argument("--subject", action="store", help="Email subject")
	parser.add_argument("--merge-data", action="store", help="CSV file with merge entries. Columns should be 'email' and the fields of the template.")
	parser.add_argument("--sender", action="store", help="Sender email")
	parser.add_argument("--password", action="store", help="Password for sender email")
	parser.add_argument("--smtp_server", action="store", help="SMTP server to send from. Defaults to Gmail. Note that for Gmail, the sender's email must have certain security features turned off. See README.md for more details.", default="smtp.gmail.com")
	parser.add_argument("--no-debug", action="store_true", help="Include this flag to really send the email. If this flag is not included, the emails will print to stdout.")
	
	args, _ = parser.parse_known_args(cmd)

	if args.help:
		parser.print_help()
		for plugin in plugin_options:
			print("-" * int(COLUMNS))
			print()
			print("Arguments for %s plugin" % plugin)
			mod = __import__("plugins.%s" % plugin, fromlist=["object"])
			mod.Plugin.get_args(cmd)
		raise SystemExit
	return args


def run_debug_server():
	"""
	Function to be run by a thread to start the email debug server. Prints all emails to stdout.
	"""
	server = DebuggingServer(('localhost', 1025), None)
	asyncore.loop()

if __name__ == "__main__":
	args = get_args(sys.argv[1:])

	# Import plugin
	if args.plugin:
		plugin = __import__("plugins.%s" % args.plugin, fromlist=["object"]).Plugin(sys.argv[1:])

	# Set up email details
	smtp_server = args.smtp_server if args.no_debug else "localhost"
	port = 465 if args.no_debug else 1025
	password = args.password
	sender_email = args.sender

	# Read in CSV with mail merge data
	data = pd.read_csv(args.merge_data, dtype=str)

	# Read in text and html email bodies
	with open(args.html) as fp:
		html_tmplt = Template(fp.read())
	with open(args.text) as fp:
		text_tmplt = Template(fp.read())

	# Read in images for email body
	imgs = []
	for img_str in args.img:
		with open(img_str, "rb") as fp:
			img = fp.read()
			maintype, subtype = mimetypes.guess_type(fp.name)[0].split('/')
			cid = make_msgid(domain=sender_email.split("@")[1])[1:-1]

			imgs.append({
				"name": img_str,
				"img": img, 
				"maintype": maintype,
				"subtype": subtype,
				"cid": cid
			})

	if args.no_debug:
		context = ssl.create_default_context()
	else:
		th = threading.Thread(target=run_debug_server)
		th.start()
		sleep(1)

	with smtplib.SMTP_SSL(smtp_server, port, context=context) if args.no_debug else smtplib.SMTP(smtp_server, port) as server:
		if args.no_debug:
			server.login(sender_email, password)

		for i, row in tqdm(data.iterrows(), total=len(data)):
			receiver_email = row["email"]

			row_mod = plugin.process_row(row) if args.plugin else row

			text = text_tmplt.substitute(row_mod)

			row_mod.update({"img%d" % i: img["cid"] for i, img in enumerate(imgs)})
			html = html_tmplt.substitute(row_mod)

			email = EmailMessage()
			email["Subject"] = args.subject
			email["From"] = args.sent_from
			email["To"] = receiver_email

			email.set_content(text)
			email.add_alternative(html, subtype="html")

			for img in imgs:
				email.get_payload()[1].add_related(img["img"],
												maintype=img["maintype"], 
												subtype=img["subtype"], 
												cid=img["cid"])
											
			server.sendmail(sender_email, receiver_email, email.as_string())

	if not args.no_debug:
		th.join()