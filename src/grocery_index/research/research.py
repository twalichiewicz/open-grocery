import os

import pandas as pd

from schemas import RETAILER_COLUMNS, SOURCE_COLUMNS
from sources import research_retailer


INPUT = "retailers.csv"
OUTPUT_DIR = "output"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    retailers = pd.read_csv(INPUT)

    retailer_results = []
    source_results = []

    for _, row in retailers.iterrows():
        retailer = row.to_dict()

        print(f"Researching {retailer['retailer']}...")

        try:
            retailer_record, sources = research_retailer(retailer)

            retailer_results.append(retailer_record)
            source_results.extend(sources)

        except Exception as exc:
            print(f"  ERROR: {exc}")

    pd.DataFrame(
        retailer_results,
        columns=RETAILER_COLUMNS,
    ).to_csv(
        f"{OUTPUT_DIR}/retailer_matrix.csv",
        index=False,
    )

    pd.DataFrame(
        source_results,
        columns=SOURCE_COLUMNS,
    ).to_csv(
        f"{OUTPUT_DIR}/sources.csv",
        index=False,
    )

    print()
    print("Research complete.")
    print(f"Retailers: {len(retailer_results)}")
    print(f"Candidate sources: {len(source_results)}")


if __name__ == "__main__":
    main()