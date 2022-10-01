# sheets-script

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install all the dependencies (make sure to use venv)

```bash
pip install -r requirements.txt
```
Create an empty database and include it's name, password... in environment variables (see example.env)
```bash
psql -U postgres
psql> CREATE DATABASE sheets;
```
Run sheets_script.py
```bash
python sheets_script.py
```
This script will create a db table if it doesn't exist and start retrieving data from google sheets spreadsheet you included in SPREADSHEET_ID environment variable.
```bash
# Orders table created from sheets_script.py
CREATE TABLE IF NOT EXISTS orders(
    id serial PRIMARY KEY NOT NULL,
    order_number INT NOT NULL,
    price_usd numeric(15,6) NOT NULL,
    delivery_date date NOT NULL,
    price_rub numeric(15,6) NOT NULL,
    UNIQUE(order_number)
);
```
Make migrations
```bash
cd sheetsapp
python manage.py migrate
```
and run the server
```bash
python manage.py runserver
```

## License
[MIT](https://choosealicense.com/licenses/mit/)
