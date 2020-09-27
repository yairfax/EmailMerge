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
from string import Template
from tqdm import tqdm
import sys
import subprocess as sp
from bs4 import BeautifulSoup
import re

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
	parser.add_argument("--plugins", action="store", choices=plugin_options, nargs="+", default=[], help="Python plugins for extra data processing. Python files should be in plugins/. See README.md for details")
	
	parser.add_argument("--html", action="store", help="HTML version of the email body. Images should be included with <img> tags with src='cid:${<img>}'. See README.md for more details.")
	parser.add_argument("--text", action="store", help="Plain text version of the email body. If --text is not specified, the html file will be converted to text, sans image tags.")
	parser.add_argument("--img", action="store", nargs="+", default=[], help="Images to be included in the email body. Images should be listed in the order they appear in the HTML file.")
	parser.add_argument("--sent-from", action="store", help="Name to show as email sender")
	parser.add_argument("--subject", action="store", help="Email subject")
	parser.add_argument("--merge-data", action="store", help="CSV file with merge entries. Columns should be 'email' and the fields of the template.")
	parser.add_argument("--sender", action="store", help="Sender email")
	parser.add_argument("--password", action="store", help="Password for sender email")
	parser.add_argument("--smtp-server", action="store", help="SMTP server to send from. Defaults to Gmail. Note that for Gmail, the sender's email must have certain security features turned off. See README.md for more details.", default="smtp.gmail.com")
	parser.add_argument("--no-debug", action="store_true", help="Include this flag to really send the email. If this flag is not included, the emails will print to stdout.")
	
	args, _ = parser.parse_known_args(cmd)

	if args.help:
		parser.print_help()
		for plugin in plugin_options:
			print("-" * int(COLUMNS))
			print()
			print("Arguments for %s plugin" % plugin)
			mod = __import__("plugins.%s" % plugin, fromlist=["object"])
			try:
				mod.Plugin.get_args(cmd)
			except SystemExit:
				# Need to pass in case of required arguments in plugin
				pass
		raise SystemExit
	return args

def run_debug_server():
	"""
	Function to be run by a thread to start the email debug server. Prints all emails to stdout.
	"""
	server = DebuggingServer(('localhost', 1025), None)
	asyncore.loop()

def compile_html_to_text(html_str):
	"""
	Compile html string to text. Removes leading whitespace and all image tags.
	Args:
		html string to convert to text
	"""
	html_str = html_str.replace('\n', '')
	html_str = re.sub(r'[\t ]+', ' ', html_str)
	html = BeautifulSoup(html_str, features='html.parser')
	text = html.get_text('\n')
	text_0 = re.sub(r'\n[ \t]*', '\n', text) # strip leading whitespace from lines
	return re.sub(r'(^\s*)|(\s*$)', '', text_0) # strip leading and trailing newliness

def compile_text_to_html(text_str, imgs):
	"""
	Compile text file to html. All text will be included in one <p> tag, and any
	images will be appended to the end of the <p> tag. All newlines will be
	replaced with <br /> tags.
	"""
	soup = BeautifulSoup()
	html_tag = soup.new_tag('html')
	

def get_html_txt(text_file, html_file, imgs):
	"""
	Read in html and text files from specified filenames. If html is not specified,
	text will be compiled to html, and vice-versa. If only a text_file is specified
	and there are images, the <img> tags will be appended to the end of the html body.
	If neither html nor txt is specified, runtime error will be raised.
	"""
	if not text_file and not html_file:
		raise RuntimeError('Need to specify either text file or html file')

	if html_file:
		with open(args.html) as fp:
			html_txt = fp.read()
	else:
		# need to convert text to html, but don't have text yet
		html_txt = None

	if text_file:
		with open(args.text) as fp:
			text_txt = fp.read()
	else:
		text_txt = compile_html_to_text(html_txt)

	if not html_txt:
		html_txt = compile_text_to_html(text_txt)

if __name__ == "__main__":
	args = get_args(sys.argv[1:])

	# Import plugin
	plugins = {plugin: __import__("plugins.%s" % plugin, fromlist=["object"]).Plugin(sys.argv[1:]) for plugin in args.plugins}

	# Set up email details
	smtp_server = args.smtp_server if args.no_debug else "localhost"
	port = 465 if args.no_debug else 1025
	password = args.password
	sender_email = args.sender

	# Read in CSV with mail merge data
	data = pd.read_csv(args.merge_data, dtype=str)

	# Read in images for email body
	imgs = []
	for img_str in args.img:
		with open(img_str, "rb") as fp:
			img = fp.read()
			maintype, subtype = mimetypes.guess_type(fp.name)[0].split('/')

			imgs.append({
				"tag": img_str.split(".")[0],
				"name": img_str,
				"img": img, 
				"maintype": maintype,
				"subtype": subtype,
			})

	# Read in text and html email bodies
	text_tmplt, html_tmplt = get_html_txt(args.text, args.html, imgs)

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
				row_mod[j] = a

			imgs_lcl = imgs.copy()

			for plugin_name, plugin in plugins.items():
				row_mod, imgs_lcl = plugin.process_row(row_mod, imgs_lcl)

			text = text_tmplt.substitute(row_mod)
			html = html_tmplt.substitute(row_mod)

			email = EmailMessage()
			email["Subject"] = args.subject
			email["From"] = args.sent_from
			email["To"] = receiver_email

			email.set_content(text)
			email.add_alternative(html, subtype="html")

			for img in imgs_lcl:
				email.get_payload()[1].add_related(img["img"],
												maintype=img["maintype"], 
												subtype=img["subtype"], 
												cid=img["tag"])
											
			server.sendmail(sender_email, receiver_email, email.as_string())

	if not args.no_debug:
		th.join()