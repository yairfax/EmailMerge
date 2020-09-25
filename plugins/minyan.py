import argparse
import pandas as pd
import numpy as np

class Plugin:
    @staticmethod
    def get_args(cmd):
        """
        Get args for minyan plugin.
        """

        parser = argparse.ArgumentParser(description="Minyan plugin that replaces numbers in CSV file with minyan locations, and performs other modifications to the data for use with the Yamim Noraim email list.")
        parser.add_argument("--location-file", required=True, help="File with location data for minyan.")
        args, _ = parser.parse_known_args(cmd)
        
        return args

    def __init__(self, cmd):
        self.args = self.get_args(cmd)

        self.locations = pd.read_csv(self.args.location_file, index_col="num", dtype=str)

    def process_row(self, row):
        """
        Substitue number in the CSV file with a location from the location file, and do other modifications for the Yamim Noraim email.
        Returns a dict with the minyan locations substituted for the numbers.

        Args:
            - row: dict-like with data from the CSV file
        """
        row_mod = {}

        for j, a in row.items():
            try:
                loc_int = int(a)
                row_mod[j] = self.locations.loc[loc_int, "location"]
            except ValueError:
                row_mod[j] = a if a and a is not np.nan and a != "" and a != " " else "Not Signed Up"
        
        return row_mod

    def func(self):
        print(self.args)