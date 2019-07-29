import main_functions
    
host_name = "http://pn108747.nist.gov:3680"
search_engine = "https://www.google.com"  # i.e. 0
# search_engine = "https://duckduckgo.com/" # i.e. 1
username="jfl2@localhost"
password="jfl2_mysql"
database_name="DBADSORPTION_SANDBOX"

main_functions.authors2()
main_functions.pairing_unknown_authors()
main_functions.scrape_authors()
main_functions.comparing_scraped()
main_functions.sql_database_writer()