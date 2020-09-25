import argparse
import csv

class Plugin:
    @staticmethod
    def get_args(argv):
        parser = argparse.ArgumentParser(description="Parse the arguments for the picnic plugin.")
        parser.add_argument("--locations-file", required=True, action="store", help="file with the location data for the picnic.")
        args, _ = parser.parse_known_args(argv)

        return args

    def __init__(self, argv):
        self.args = self.get_args(argv)

        self.locations = {}

        with open(self.args.locations_file, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Results in {num: {"location": location, "location_img": location_img}}
                index = row["num"]
                del row["num"]
                row["location_img"] = row["location_img"].split(".")[0]
                self.locations[index] = row

    def process_row(self, row):
        index = row["location"]
        row["location"] = self.locations[index]["location"]
        row["location_img"] = self.locations[index]["location_img"]

        return row