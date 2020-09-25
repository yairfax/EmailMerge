# EmailMerge

EmailMerge sends out tailored emails to a list of recipients using a template. It is similar in function to Microsoft Word's mail merge funcionality.

## Installation

Requires Python 3. To install requirements, run

```bash
pip install -r requirements.txt
```

## Usage

EmailMerge uses Python templating to format its emails. For more on that see the [Templating](#templating) section. It also supports a plugin system to perform extra processing on email bodies. For more on the plugins, see the [Plugin](#plugin) section.

By default, EmailMerge runs in debug mode. See [Debugging](#debugging)

To run EmailMerge, run `driver.py`. The arguments `driver.py` takes are as follows.

| Tag             | Description                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------ |
| `--help`        | Print the help message                                                                                             |
| `--html`        | An HTML version of the email body to send.                                                                         |
| `--text`        | A plaintext version of the email body to send.                                                                     |
| `--img`         | Optional images to include in the body of the email. There can be mulitple images.                                 |
| `--sent-from`   | String to include as the sender of the email. NOT the sender's email address.                                      |
| `--subject`     | Subject of the email.                                                                                              |
| `--merge-data`  | CSV file with the fields to be merged into the email. See [Templating](#templating) for details.                   |
| `--sender`      | Email address to send from.                                                                                        |
| `--password`    | Password for the email address to send from.                                                                       |
| `--smtp-server` | SMTP server for the given email address. Defaults to Gmail.                                                        |
| `--no-debug`    | Don't debug. By default, EmailMerge prints out all emails to `stdout`. To actually send emails, include this flag. |
| `--plugins`     | Optional plugins to perform further modifications to the data. See [Plugins](#plugins) for details                 |

### Security

Note that Gmail requires certain security features be disabled for us to connect to their SMTP server using Python. It is recommended either that you re-enable them after using EmailMerge, or that you create a new email account only for use with EmailMerge. You can disable the security features [here](https://myaccount.google.com/lesssecureapps).

### Debugging

By default, EmailMerge runs in debug mode. This will print all the emails to `stdout`. Note that if you're including images in your email they will be base64 encoded in stdout, so the output will likely be unreadable. To trunucate the output, consider piping EmailMerge through `head`:

```bash
python driver.py [...] | head -n 50
```

To actually send emails, include the `--no-debug` flag.

## Templating

### CSV Data Source

EmailMerge takes a CSV file with the merge data to send out emails. It expects one column called `email`. Any other columns should match template fields in the HTML and text files. For example, this CSV file would match this HTML file and an equivalent text file.

```csv
email,name,favorite_food
yair@fax.com,Yair Fax,steak
ezra@fax.com,Ezra Fax,pizza
neima@fax.com,Neima Fax,hot dogs
```

```html
<html>
  <body>
    <p>Hi ${name},</p>
    <p>
      I'm hosting a dinner party, and we'll be serving ${favorite_food}. Can you
      make it?
    </p>
  </body>
</html>
```

### Images

EmailMerge supports including images in your email as attachments and embedded elements. Images are included from the command line using the `--img` flag. Note that this flag is optional, images need not be included. It also accepts any number of arguments, so you can include more than one image in your email.

```bash
python driver.py [...] --img patio.jpg lawn.jpg
```

To embed these images in your email, use `<img>` tags with `src='cid:${<img>}'` in your HTML file, where `<img>` is the filename of the image without the extension. So for the previous example, this is what your HTML would look like:

```html
<html>
  <body>
    <p>Hi ${name},</p>
    <p>
      I'm hosting a dinner party, and we'll be serving ${favorite_food}. Can you
      make it? <br />
      Because of COVID we can't host everyone in the same place, can you pick
      where you would rather sit? This is a picture of our patio.
      <img src="cid:${patio}" />
      This is a picture of our lawn.
      <img src="cid:${lawn}" />
    </p>
  </body>
</html>
```

Note that embedded images should only be included in the HTML file, not the plaintext file. If the email client doesn't support HTML, the images will be included as attachments.

## Plugins

EmailMerge supports Python plugins to perform further modifications on the merge data before it's formatted for the email. Plugins should go in the plugin folder. As an example, we will write a plugin that transforms the full name into only the first name before formatting the email. We start by creating `name.py` in the `plugins` folder.  
In our plugin file, we define a class called `Plugin`:

```python
class Plugin:

```

EmailMerge expects `Plugin` to have a `process_row` method, which takes a dict-like `row` as a parameter, modifies it, and returns it. It also expects an `__init__` function that takes `argv` as a parameter, and a static `get_args` method that also takes `argv` as a parameter. For an example that uses this, see the [next section](#an-involved-example). For our example, we can write it as such.

```python
def __init__(self, argv):
    pass

@staticmethod
def get_args(argv):
    pass

def process_row(self, row):
    row["name"] = row["name"].split(" ")[0]

    return row
```

In our example, this will replace all full names with only first names, so that the email reads `Hi Yair,` instead of `Hi Yair Fax,`.  
The plugin is invoked as such:

```bash
python driver.py --plugins name [...]
```

Note that plugins can be stacked on top of each other. Plugins run in the order listed, so changes from one plugin may override changes from a previous one. In general it is not recommended to stack plugins that modify the same fields, so that the listing of the plugins can be order agnostic. Note also that the `dict` of fields is completely replaced by what the plugin returns, so the plugin is responsible for maintaining any fields it doesn't modify.

### An Involved Example

Let's do a bit of a more involved example to show why `get_args` is necessary. In this example, we are telling the guests in our dinner party where they'll be sitting, but in our CSV file we only have their locations listed as numbers.

```csv
email,name,favorite_food,location
yair@fax.com,Yair Fax,steak,1
ezra@fax.com,Ezra Fax,pizza,2
neima@fax.com,Neima Fax,hot dogs,1
```

We have a separate file `locations.csv`, that has the locations corresponding to the numbers, and the names of the images of the places they'll be sitting.

```csv
num,location
1,lawn
2,patio
```

We also have to update our HTML and text files accordingly:

```html
<html>
  <body>
    <p>Hi ${name},</p>
    <p>
      I'm hosting a dinner party, and we'll be serving ${favorite_food}. Can you
      make it? <br />
      Because of COVID we can't host everyone in the same place, so you're going
      to be sitting on the ${location}. <br />
    </p>
  </body>
</html>
```

We then need to write our plugin to replace `location` in our main merge data with the actual location string from `locations.csv`.

EmailMerge uses the [argparse library](https://docs.python.org/3/library/argparse.html) to parse its arguments, as should the static method `get_args` in the plugin. In fact, when the user calls `python driver.py -h`, EmailMerge will call `get_args` in each plugin and display its `argparse` help.  
For our example, `get_args` needs to take in `locations.csv`.

```python
import argparse

@staticmethod
def get_args(argv):
    parser = argparse.ArgumentParser(description="Parse the arguments for the picnic plugin.")
    parser.add_argument("--locations-file", required=True, action="store", help="file with the location data for the picnic.")
    args, _ = parser.parse_known_args(argv)

    return args
```

In our `__init__` function we need to parse the arguments and store anything that we'll need for formatting later. In our example that means reading in the CSV file with the location data and storing it.

```python
import csv

def __init__(self, argv):
    self.args = self.get_args(argv)

    self.locations = {}

    with open(self.locations_file, "r") as file:
        reader = csv.reader(csvfile)
        for row in reader:
            # Results in {num: location}
            self.locations[row[0]] = row[1]
```

We then need to write our `process_row` function which will actually modify the data. The value in the row as it is is the number of the location, and we need ot replace it with the location string.

```py
def process_row(self, row):
    row["location"] = self.locations[row["locations"]]
```

And we're done! We invoke this plugin thus:

```bash
python driver.py --plugins picnic --locations-file locations.csv [...]
```

As stated above, we can stack these plugins atop one another:

```bash
python driver.py --plugins picnic name --locations-file locations.csv [...]
```

Note that images cannot be used within the data source or in plugins. Meaning that images can only be included statically in the original email body, and the user cannot specify an image file in the merge data to be included specifically for each email. This will be fixed in an update.
