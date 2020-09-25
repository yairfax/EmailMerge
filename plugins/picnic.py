import argparse
import csv

class Plugin:
    def __init__(self, argv):
        self.args = self.get_args(argv)

        self.locations = {}

        with open(self.locations_file, "r") as file:
            reader = csv.reader(csvfile)
            for row in reader:
                # Results in {num: location}
                self.locations[row[0]] = row[1]

    @staticmethod
    def get_args(argv):
        parser = argparse.ArgumentParser(description="Parse the arguments for the picnic plugin.")
        parser.add_argument("--locations-file", required=True, action="store", help="file with the location data for the picnic.")
        args, _ = parser.parse_known_args(argv)

        return args

    def process_row(self, row):
        row["location"] = self.locations[row["locations"]]