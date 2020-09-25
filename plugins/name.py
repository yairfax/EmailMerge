class Plugin:
    def __init__(self, argv):
        pass

    @staticmethod
    def get_args(argv):
        pass

    def process_row(self, row):
        row["name"] = row["name"].split(" ")[0]

        return row