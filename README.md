# nist_adsorption_db_sanitize

Project to cross-reference authors and obtain isotherm data.

Run main_runnable.py (with python3) to run the script.

runnable_main.py consists of the source files in this workflow:
authors2.ipynb -> pairing_unknown_authors.ipynb -> scrape_authors.ipynb -> comparing_scraped.ipynb -> sql_database_writer.ipynb

Overall, the script will grab the authors and paper bibliography information from the database API (at a given hostname) and match them according to duplicates and unknown authors with matches in authors2 and pairing_unknown_authors. It will then scrape researchgate (via Google searches) for the papers' pages and associate authors with URLs in scrape_authors. The URLs will be used to verify duplicates/unknowns' identities in comparing_scraped and it will be written to the database in sql_database_writer.