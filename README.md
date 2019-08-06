# nist_adsorption_db_sanitize

Project to cross-reference authors and obtain isotherm data.

Run main_runnable.py (with python3) to run the script.

main_functions.py consists of the source files (the ipynb notebooks) and main_runnable.py runs it in this workflow:
authors2.ipynb -> pairing_unknown_authors.ipynb -> scrape_authors.ipynb -> comparing_scraped.ipynb -> sql_database_writer.ipynb

Overall, the script will grab the authors and paper bibliography information from the database API (at a given hostname) and match them according to duplicates and unknown authors with matches in authors2 and pairing_unknown_authors. It will then scrape researchgate (via Google searches) for the papers' pages and associate authors with URLs in scrape_authors. The URLs will be used to verify duplicates/unknowns' identities in comparing_scraped and it will be written to the database in sql_database_writer.

Originally, the methodology for scraping was to search the DOI on the ResearchGate website. This was done by simply entering the DOI in the search box. After a design change in ResearchGate's search, a search had to be made then the "Data" tab had to be clicked on. Eventually, this functionality was removed as well. Now the scraping is done by searching "researchgate.net" and the DOI on google.com and clicking on "I'm feeling lucky" to immediately open the webpage. This isn't foolproof and there are occasionally time where it doesn't work. 1) ResearchGate may not host the paper. 2) Very rarely ResearchGate will open a related paper that reference the paper being searched. 

Unsure author match output format:
Unknown Author:

Unknown Author ID\
Unknown Author Name, Unknown Author URL\
Small Divider\
Author match index in list, Author match ID\
Author match name, Author match URL\
(Repeat)\
Large Divider (indicates next entry)

Duplicate Author:

Duplicate author index, Duplicate author id\
Duplicate author name, Duplicate author URL\
Large Divider (Indicates new entry)\