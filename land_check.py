import json
import os
from realestate_com_au import RealestateComAu

# Email stuff
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# SECRETS IN GITHUB:
# FROM_ADDR - string
# TO_ADDRS - List in '' eg '["abc", "sdf"]'
# MAIL_KEY - string

api = RealestateComAu()

max_price = 1000000         # $
min_land_size = 100         # ha
max_dollars_per_ha = 1500   # $/ha

# Get property listings
listings = api.search(locations=["WA"],
                        channel="buy",
                        exclude_no_sale_price=True,
                        max_price=max_price,
                        min_land_size=min_land_size*10000)
old_properties = []
new_properties = []
stored_urls = []
sent_urls = []

with open("data.json", "r") as file:
    try:
        stored_urls = json.load(file)
    except json.JSONDecodeError:
        pass
    except FileNotFoundError:
        pass

for property in listings:
    if property.land_size_unit == "ac":
        property.land_size = property.land_size * 0.404686
        property.land_size_unit = "ha"
    elif property.land_size_unit == "m2":
        property.land_size = property.land_size * 1e-4
        property.land_size_unit = "ha"

    if property.land_size_unit != "ha" or property.price is None:
        continue

    dollars_per_ha = property.price / property.land_size

    if dollars_per_ha <= max_dollars_per_ha:
        if property.url not in stored_urls:
            new_properties.append(property)
        else:
            old_properties.append(property)
        sent_urls.append(property.url)

if len(new_properties) > 0:

    smtp = smtplib.SMTP("smtp.fastmail.com", 587)
    smtp.ehlo()
    smtp.starttls()

    smtp.login(os.environ["FROM_ADDR"], os.environ["MAIL_KEY"])

    msg = MIMEMultipart()
    msg["From"] = os.environ["FROM_ADDR"]
    
    if len(new_properties) == 1:
        msg["Subject"] = str("1 new property uploaded")
    else:
        msg["Subject"] = str("%d new properties uploaded" % len(new_properties))
        
    msg.attach(MIMEText("""
    All properties found on RealEstate.com.au for under
    $%d of over %dha and with a land value less than $%d/ha."""
    % (max_price, min_land_size, max_dollars_per_ha)))

    new_text = "New\n"
    for this in new_properties:
        new_text += this.url + "\n"
        new_text \
            += "Value: " + str(round(this.price / this.land_size)) + "$/ha" \
            + "\t Price: $" + str(this.price) \
            + "\t Area: " + str(this.land_size) + "ha\n\n"
    msg.attach(MIMEText(new_text))

    if len(old_properties) > 0:
        old_text = "Old\n"
        for this in old_properties:
            old_text += this.url + "\n"
            old_text \
                += "Value: " + str(round(this.price / this.land_size))+"$/ha" \
                + "\t Price: $" + str(this.price) \
                + "\t Area: " + str(this.land_size) + "ha\n\n"
        msg.attach(MIMEText(old_text))

    msg.attach(MIMEText("To contribute go to: https://github.com/gerrygralton/land_check"))

    smtp.sendmail(from_addr=os.environ["FROM_ADDR"],
                    to_addrs=json.loads(os.environ["TO_ADDRS"]),
                    msg=msg.as_string())

with open("data.json", "w") as file:
    json.dump(sent_urls, file)
