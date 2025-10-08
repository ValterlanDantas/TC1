import csv
import os
import time
from urllib.parse import urljoin, urlparse

from tc_01.config.variables import Config
import requests
from bs4 import BeautifulSoup


def get_with_retry(url, max_retries=3, delay=2):
    """
    Faz uma requisição HTTP com retry automático para uma URL específica, com um máximo de tentativas e um atraso entre tentativas. Retorna a resposta da requisição.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=20)
            response.encoding = "utf-8"
            return response
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                return None
    return None


def get_parent_url(url):
    """
    Retorna a URL um nível acima da URL fornecida. Trata-se de uma função auxiliar para o scraping.
    Exemplo: 'https://books.toscrape.com/catalogue/category/books/mystery_3/index.html'
    retorna: 'https://books.toscrape.com/catalogue/category/books/mystery_3/'
    """
    parsed_url = urlparse(url)

    path_parts = parsed_url.path.rstrip("/").split("/")

    if path_parts and path_parts[-1]:
        path_parts = path_parts[:-1]

    new_path = "/".join(path_parts) + "/"

    return f"{parsed_url.scheme}://{parsed_url.netloc}{new_path}"


def get_categories(url):
    """
    Retorna todas as categorias do site, em um dicionário de forma organizada, de forma que possa ser usado para o scraping dos livros.
    """
    response = get_with_retry(url)
    if response is None:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    table_categories = soup.find_all("ul")
    categories = table_categories[2].find_all("a")
    dict_categories = []
    for category in categories:
        dict_categories.append(
            {"name": category.text.strip(), "href": category.get("href")}
        )
    return dict_categories


def get_books(categories):
    """
    Coleta os livros de todas as categorias passadas como parâmetro
    """
    list_books = []
    quantity_books = 0
    for category in categories:
        url = f"{Config.URL_BASE}{category['href']}"
        response = get_with_retry(url)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, "html.parser")
        soup_books = soup.find_all("article", class_="product_pod")
        for book in soup_books:
            quantity_books += 1
            list_books.append(
                {
                    "id": quantity_books,
                    "title": book.find("h3").find("a").get("title").strip(),
                    "price": book.find("p", class_="price_color").text.strip(),
                    "rating": book.find("p", class_="star-rating")
                    .get("class")[1]
                    .strip(),
                    "availability": book.find(
                        "p", class_="instock availability"
                    ).text.strip(),
                    "category": category["name"].strip(),
                    "image": book.find("img").get("src").strip(),
                }
            )
        next_page = soup.find("li", class_="next")
        if next_page:
            url_next_page = get_parent_url(
                f"{Config.URL_BASE}{category['href']}"
            )
            url_next_page = url_next_page + next_page.find("a").get("href")
            response_next_page = get_with_retry(url_next_page)
            if response_next_page is None:
                continue
            while response_next_page.status_code == 200:
                soup_next_page = BeautifulSoup(response_next_page.text, "html.parser")
                soup_books_next_page = soup_next_page.find_all(
                    "article", class_="product_pod"
                )
                for book in soup_books_next_page:
                    quantity_books += 1
                    list_books.append(
                        {
                            "id": quantity_books,
                            "title": book.find("h3").find("a").get("title").strip(),
                            "price": book.find("p", class_="price_color").text.strip(),
                            "rating": book.find("p", class_="star-rating")
                            .get("class")[1]
                            .strip(),
                            "availability": book.find(
                                "p", class_="instock availability"
                            ).text.strip(),
                            "category": category["name"].strip(),
                            "image": book.find("img").get("src").strip(),
                        }
                    )
                next_page = soup_next_page.find("li", class_="next")
                if next_page:
                    category_base_url = get_parent_url(
                        f"{Config.URL_BASE}{category['href']}"
                    )
                    url_next_page = urljoin(
                        category_base_url, next_page.find("a").get("href")
                    )
                    response_next_page = get_with_retry(url_next_page)
                    if response_next_page is None:
                        break
                else:
                    break
    return list_books


def save_to_csv(books, filename=Config.CSV_FILE):
    """
    Salva os dados dos livros em um arquivo CSV
    """
    path_file = os.path.join(Config.DATA_DIR, filename)
    fieldnames = ["id", "title", "price", "rating", "availability", "category", "image"]

    with open(path_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")

        writer.writeheader()

        writer.writerows(books)


if __name__ == "__main__":
    print("Iniciando a coleta de dados...")
    categories = get_categories(Config.URL_BASE)
    books = get_books(categories)
    save_to_csv(books)
    print("Coleta de dados concluída com sucesso!")
