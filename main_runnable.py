import main_functions
   
# Parameters to modify
host_name = "http://pn108747.nist.gov:3680"
search_engine = "https://www.google.com"  # i.e. 0
# search_engine = "https://duckduckgo.com/" # i.e. 1. DON'T USE THIS FOR NOW (not very high accuracy)
username="jfl2@localhost"
password="jfl2_mysql"
database_name="DBADSORPTION_SANDBOX"

# Function calls, actually runs the script
main_functions.authors2(host_name)
print("authors2 done")
time.sleep(1)

main_functions.pairing_unknown_authors()
print("pairing_unknown_authors done")
time.sleep(1)

main_functions.scrape_authors(search_engine)
print("scrape_authors done")
time.sleep(1)

main_functions.comparing_scraped()
print("comparing_scraped done")
time.sleep(1)

main_functions.sql_database_writer(username, password, database_name)
print("sql_database_writer done")