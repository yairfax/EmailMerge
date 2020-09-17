import smtplib, ssl
import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--password", action="store", required=True)
parser.add_argument("--data", action="store", required=True)
parser.add_argument("--message", action="store", required=True)
parser.add_argument("--sender", action="store", required=True)
args = parser.parse_args()

smtp_server = "smtp.gmail.com"
port = 465
password = args.password
sender_email = args.sender

data = pd.read_csv(args.data, dtype=str)
msg = open(args.message).read()

context = ssl.create_default_context()

with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
	server.login(sender_email, password)

	locations = {
		"1": "Chapel Fields",
		"2": "Behind Knight Hall",
		"3": "Mowatt Parking Lot",
		"4": "Lot O (Across from Domain)"
	}

	for i, row in data.iterrows():
		receiver_email = row["email"]

		row = {j: locations[a] if a in locations else (a if a != "" and a != " " else "Not Signed Up") for j, a in row.items()}

		body = msg % (row["name"], row["name"].split()[0],
		row["Maariv 1"], row["Shacharit Day 1"],
		row["Mussaf Day 1"], row["Mincha 1"],
		row["Maariv 2"], row["Shacharit Day 2"],
		row["Mussaf Day 2"], row["Mincha 2"],
		row["Maariv 3"])

		server.sendmail(sender_email, receiver_email, body)

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