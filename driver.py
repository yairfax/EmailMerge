import smtplib, ssl
import argparse
import pandas as pd
from os import system
from smtpd import DebuggingServer
import asyncore
import threading
from time import sleep
from email.message import EmailMessage
import mimetypes
from email.utils import make_msgid
from string import Template
from tqdm import tqdm
import numpy as np

import sys

def run_debug_server():
	server = DebuggingServer(('localhost', 1025), None)
	asyncore.loop()

def get_args():
	parser = argparse.ArgumentParser(description="Mail merge python script. Email body files should include Python template fields that match the headers of the CSV files. For example, a column 'data1' in the CSV file should have a correspoding ${data1} in the template. Note that all spaces in CSV headers are replaced with underscores, and all characters are put in lower case, so 'Data 1' becomes '${data_1}'.")
	parser.add_argument("--html", action="store", required=True, help="HTML version of the email body. Images should be included with <img> tags with src='cid:${img0}', with increasing integers for each image.")
	parser.add_argument("--text", action="store", required=True, help="Plain text version of the email body")
	parser.add_argument("--img", action="store", nargs="+", default=[], help="Images to be included in the email body. Images should be listed in the order they appear in the HTML file.")
	parser.add_argument("--sent-from", action="store", required=True, help="Name to show as email sender")
	parser.add_argument("--subject", action="store", required=True, help="Email subject")
	parser.add_argument("--data", action="store", required=True, help="CSV file with entries. Columns should be 'name' and 'email', followed by the fields of the template.")
	parser.add_argument("--sender", action="store", required=True, help="Sender email")
	parser.add_argument("--password", action="store", required=True, help="Password for sender email")
	parser.add_argument("--smtp", action="store", help="SMTP server to send from. Defaults to Gmail. Note that for Gmail, the sender's email must have certain security features turned off. See README.md for more details.", default="smtp.gmail.com")
	parser.add_argument("--locations", action="store", required=True)
	parser.add_argument("--no-debug", action="store_true", help="Include this flag to really send the email. If this flag is not included, the emails will print to stdout.")
	args = parser.parse_args()

if __name__ == "__main__":
	args = get_args()

	smtp_server = args.smtp if args.no_debug else "localhost"
	port = 465 if args.no_debug else 1025
	password = args.password
	sender_email = args.sender

	locations = pd.read_csv(args.locations, index_col="num", dtype=str)
	data = pd.read_csv(args.data, dtype=str)
	with open(args.html) as fp:
		html_tmplt = Template(fp.read())
	with open(args.text) as fp:
		text_tmplt = Template(fp.read())

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

			row_mod = {}

			for j, a in row.items():
				j = j.lower().replace(" ", "_")
				try:
					loc_int = int(a)
					row_mod[j] = locations.loc[loc_int, "location"]
				except ValueError:
					row_mod[j] = a if a and a is not np.nan and a != "" and a != " " else "Not Signed Up"
			row_mod["name"] = row_mod["name"].split()[0]

			# row = {j: locations[a] if a in locations else (a if a != "" and a != " " else "Not Signed Up") for j, a in row.items()}

			text = text_tmplt.substitute(row_mod)

			row_mod.update({"img%d" % i: img["cid"] for i, img in enumerate(imgs)})
			html = html_tmplt.substitute(row_mod)

			email = EmailMessage()
			email["Subject"] = args.subject
			email["From"] = args.sent_from
			email ["To"] = receiver_email

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