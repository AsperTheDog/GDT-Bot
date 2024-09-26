import csv
import sqlite3 as SQLite

def main():
    conn = SQLite.connect('src/data_files/database.sqlite')
    cursor = conn.cursor()
    with open("src/data_files/other/books.csv", 'r') as data:
        csvData = csv.DictReader(data)
        for entry in csvData:
            pages = entry["length"]
            if pages == "":
                pages = 0
            else:
                pages = int(pages)
            cursor.execute("UPDATE items SET length = ? WHERE name = ?", (pages, entry["name"]))
    conn.commit()

if __name__ == "__main__":
    main()