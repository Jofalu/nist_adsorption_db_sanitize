import main_functions
import time
   
# Parameters to modify
host_name = "http://pn108747.nist.gov:3680" # specified the API host up here
search_engine = "https://www.google.com"  # i.e. 0 or "https://duckduckgo.com/" i.e. 1 (don't use duckduckgo)
username="jfl2@localhost"
password="jfl2_mysql"
database_name="DBADSORPTION_SANDBOX"

# Function calls, actually runs the script
print("Beginning authors2")
main_functions.authors2(host_name)
print("authors2 done")
time.sleep(1)

print("Beginning pairing_unknown_authors")
main_functions.pairing_unknown_authors()
print("pairing_unknown_authors done")
time.sleep(1)

print("Beginning scrape_authors")
main_functions.scrape_authors(search_engine)
print("scrape_authors done")
time.sleep(1)

print("Beginning comparing_scraped")
main_functions.comparing_scraped()
print("comparing_scraped done")
time.sleep(1)

print("Beginning sql_database_writer")
main_functions.sql_database_writer(username, password, database_name)
print("sql_database_writer done")
