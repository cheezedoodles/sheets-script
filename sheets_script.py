import os
from functools import lru_cache
from datetime import datetime
import time
import psycopg2
import xmltodict
import requests
from decimal import Decimal

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

SAMPLE_SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SAMPLE_RANGE_NAME = "A2:D"

DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ["DB_PORT"]

SLEEPING_TIME = 30 # in seconds


@lru_cache()
def get_currency_rates(ttl_hash=None):  # basically memoization with 4 hours duration
    """
    Returns xml-like dict of today's rates from cbr.ru
    """
    current_date = datetime.today().date().strftime("%d/%m/%Y")
    response = requests.get(
        f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={current_date}"
    )
    currencies = xmltodict.parse(response.content)
    return currencies


def get_ttl_hash(seconds=14400):  # 4 hours by default
    """
    Return the same value withing `seconds` time period
    """
    return round(time.time() / seconds)


def convert_to_rub(price_usd, currencies):
    price_rub = None
    for i in currencies["ValCurs"]["Valute"]:
        if i["@ID"] == "R01235":
            price_rub = Decimal(i["Value"].replace(",", ".")) * price_usd
    return price_rub


def main():

    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)

        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
            .execute()
        )
        values = result.get("values", [])

        if not values:
            print("No data found.")
            return
        try:
            conn = psycopg2.connect(
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
            )
            cur = conn.cursor()
            cur.execute(
                """
        
                    CREATE TABLE IF NOT EXISTS orders(
                    id serial PRIMARY KEY NOT NULL,
                    order_number INT NOT NULL,
                    price_usd numeric(15,6) NOT NULL,
                    delivery_date date NOT NULL,
                    price_rub numeric(15,6) NOT NULL,
                    UNIQUE(order_number)
                    );
        """
            )
            conn.commit()
            conn.close()
            print("Database initialized successfully")
        except:
            print("Database did not initialize successfully")
        while True:
            print('retrieving data...')
            conn = psycopg2.connect(
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
            )
            cur = conn.cursor()

            cur.execute("SELECT id FROM orders;")
            existing_ids = cur.fetchall()

            cur.execute("SELECT count(*) FROM orders;")
            id_count = cur.fetchone()[0]

            blank_id = 0
            for row in values:
                try:
                    id = int(row[0])
                    order_number = int(row[1])
                    price_usd = Decimal(row[2])
                    delivery_date = datetime.strptime(row[3], "%d.%m.%Y").date()
                    currencies = get_currency_rates(ttl_hash=get_ttl_hash())
                    price_rub = convert_to_rub(
                        price_usd=price_usd, currencies=currencies
                    )
                except:
                    blank_id += 1

                    cur.execute(
                        """

                        DELETE FROM orders WHERE id = %s;

                    """,
                        (blank_id,),
                    )
                    continue

                blank_id = id
                s_id = (id,)

                if s_id not in existing_ids:
                    if id > id_count:
                        cur.execute(
                            """

                            INSERT INTO orders (id, order_number, price_usd, delivery_date, price_rub)
                            VALUES (%s, %s, %s, %s, %s);

                        """,
                            (
                                id,
                                order_number,
                                price_usd,
                                delivery_date,
                                price_rub,
                            ),
                        )
                else:
                    cur.execute(
                        """

                            UPDATE orders 
                            SET order_number = %s, price_usd = %s, delivery_date = %s, price_rub = %s
                            WHERE id = %s;

                        """,
                        (
                            order_number,
                            price_usd,
                            delivery_date,
                            price_rub,
                            id,
                        ),
                    )
            conn.commit()
            conn.close()

            time.sleep(SLEEPING_TIME)
            result = (
                sheet.values()
                .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
                .execute()
            )
            values = result.get("values", [])
    except HttpError as err:
        print(err)


if __name__ == "__main__":
    main()
