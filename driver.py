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

from sys import exit

def run_debug_server():
	server = DebuggingServer(('localhost', 1025), None)
	asyncore.loop()

parser = argparse.ArgumentParser()
parser.add_argument("--html", action="store", required=True)
parser.add_argument("--text", action="store", required=True)
parser.add_argument("--img", action="store", nargs="+", default=[])
parser.add_argument("--sent-from", action="store", required=True)
parser.add_argument("--subject", action="store", required=True)
parser.add_argument("--data", action="store", required=True)
parser.add_argument("--sender", action="store", required=True)
parser.add_argument("--password", action="store", required=True)
parser.add_argument("--locations", action="store", required=True)
parser.add_argument("--no-debug", action="store_true")
args = parser.parse_args()

smtp_server = "smtp.gmail.com" if args.no_debug else "localhost"
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

	for i, row in data.iterrows():
		receiver_email = row["email"]

		row_mod = {}

		for j, a in row.items():
			j = j.lower().replace(" ", "_")
			try:
				loc_int = int(a)
				row_mod[j] = locations.loc[loc_int, "location"]
			except ValueError:
				row_mod[j] = a if a != "" and a != " " else "Not Signed Up"
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

# shtick_signature = """\
# Daniella Bloch, Gabbait
# Scott Sandor, Gabbai Rishon
# Ryan Sweren, Gabbai Sheni
# Gabbait Shenit, Emotional Support, and Real Power In Kedma, Miriam Charnoff
# Gabbai Emeritus, Ari Israel
# Gabbai Emeritus Emereitus and Resident Coder, Yair Fax
# Gabbait Emeritusit, Tali Kosowski
# Amos, Amos
# Oh Right He Was Gabbai, Amitai Diament
# Coup Gabbai, Yoni Rawson
# Coup Gabbai Sheni, Eitan Griboff
# Coup Gabbai Emeritus, Yaacov Greenspan
# Keter, Mikey Pollack
# """