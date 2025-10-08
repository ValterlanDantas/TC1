from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).parents[1]
    DATA_DIR = BASE_DIR / "data"
    URL_BASE = "https://books.toscrape.com/"
    CSV_FILE = DATA_DIR / "books_data.csv"
