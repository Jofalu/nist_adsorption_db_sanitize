import json # used for managing the JSON files from API
import urllib # fetch URl of API
from pprint import pprint # just for printing values for human use
from collections import Counter # used for determining duplicate names

from copy import deepcopy

import time
import sys
import datetime
import random
from bs4 import BeautifulSoup
from unidecode import unidecode
from webdriver_manager.firefox import GeckoDriverManager
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import os

import re
import itertools

import mysql.connector as mariadb

def authors2(host_name):
    """
    Loads authors and papers from API and determines duplicate/unknown authors, writing them to duplicate_authors.txt and unknown_authors.txt.
    
    Parameters:
    host_name: name of host of API (e.g. "http://pn108747.nist.gov:3680" or "http://dirac.nist.gov")
    """

    # Loads the authors (and their IDs) to json
    authors = json.load(urllib.request.urlopen(host_name + "/adsorption.nist.gov/isodb/api/authors.json"))
    # Loads API call for papers
    papers = json.load(urllib.request.urlopen(host_name + "/adsorption.nist.gov/isodb/api/minimalbiblio.json"))
    # Writes papers to file 
    with open("./stored_authors/papers.txt", "w") as papers_file:
        pprint(papers, stream = papers_file)
        
    # Writes to a file ID name pairings so other scripts won't have to load the authors.json file. 
    # Also provides a method to access names from an author_id
    authors_ids = {}
    for person in authors:
        authors_ids[person["author_id"]] = [person["given_name"], person["middle_name"], person["family_name"]]
    with open("./stored_authors/authors_ids.txt", "w") as ids_file:
        pprint(authors_ids, stream = ids_file)
        
    # Generates a dictionary of authors last names and their associated first names
    authors_names = {}
    for person in authors:
        if person["given_name"]:
            first_name = person["given_name"]
        else: 
            first_name = ""
        id = person["author_id"]
        last_name = person["family_name"]
        # Checks whether to initialize or append entry
        if last_name not in authors_names.keys():
            authors_names[last_name] = [ (first_name, id) ]
        else:
            authors_names[last_name].append( (first_name, id) )
            
    # Sorts the names to place similar/same names closer to each other for human viewing
    for last_name, first_name in authors_names.items():
        first_name.sort()
        
    # Generates a dictionary of authors whose first names are just initials or contain no first name at all
    unknown_authors = {}
    matchless_authors = []
    for last_name, first_names in authors_names.items():          # Iterates through last names
        for person in first_names:                                # Iterates through first names
            if ("." in person[0] and len(person[0]) <= 2) or person[0] == "": # Checks if first name initial only or empty
                unknown_authors[ person[1] ] = []                 # Initializes the list associated with unknown person's id

    # Pairs the unknown authors with possible matches
    for unknown, matches in unknown_authors.items():
        for person in authors_names[authors_ids[unknown][2]]:
            # Case of empty first name unknown, anyone could match
            if authors_ids[unknown][0] == "" and person[1] != unknown: 
                matches.append( person[1] )

            # Only matches with same first letter
            elif authors_ids[unknown][0] != "" and person[1] != unknown and person[0][0] == authors_ids[unknown][0][0]: 
                matches.append( person[1] )
        if not matches: # If the author has no matches, they're unique, this list is to pop them later
            matchless_authors.append(unknown)

    # Write all of the unknowns, even with no matches to a file
    with open("./stored_authors/all_unknown_authors.txt", "w") as unknowns_file:
        pprint(unknown_authors, stream = unknowns_file)

    # Remove matchless authors from the dictionary since they are unique
    for author in matchless_authors:
        unknown_authors.pop(author)

    # Finding duplicate names
    duplicate_authors = {}
    # Iterates through all authors last names
    for last_name, first_names in authors_names.items():
        if len(first_names) > 1: # eliminates last names with only one associated person
            temp_list = []       # temporary list for names to count with Counter
            for person in first_names:
                if len(person[0]) >= 2 and "." not in person[0] and person[0] != "": # Ignores unknown names, covered by other case
                    temp_list.append(person[0])
            temp_counter = Counter(temp_list) # Counters instances of first names
            for first_name, freq in temp_counter.items():
                if freq > 1:
                    duplicate_authors[ (first_name, last_name) ] = [] # Append to list of duplicates 
            for duplicate, ids in duplicate_authors.items(): # Adds author_ids to the duplicate list 
                for person in first_names:
                    if person[0] == duplicate[0] and last_name == duplicate[1]: 
                        ids.append(person[1])
    
    # Writing all of the unknown authors to file
    with open("./stored_authors/unknown_authors.txt", "w") as unknowns_file:
        pprint(unknown_authors, stream = unknowns_file)
    # Writing all of the duplicate authors to file
    with open("./stored_authors/duplicate_authors.txt", "w") as duplicates_file:
        pprint(duplicate_authors, stream = duplicates_file)

def pairing_unknown_authors():
    """
    Associates papers with authors and writes the pairing to a dictionary {author : list of DOIs).
    """
    
    # Loads the papers to json from text file
    with open("./stored_authors/papers.txt", encoding="utf8") as papers_file:
        papers = eval(papers_file.read())
    # Loads authors and their ids to json from text file
    with open("./stored_authors/authors_ids.txt", encoding="utf8") as authors_file:
        authors_ids = eval(authors_file.read())
    # Loads duplicate authors
    with open("./stored_authors/duplicate_authors.txt") as dup_file:
        duplicate_authors = eval(dup_file.read())
    # Loads unknown authors
    with open("./stored_authors/unknown_authors.txt") as unk_file:
        unknown_authors = eval(unk_file.read())
        
    # Initializes the author/paper dict: tracks papers for unknown and duplicate authors
    authors_and_papers = {}
    # Adds unknown authors to authors_and_papers
    for unknown, pairs in unknown_authors.items():
        authors_and_papers[unknown] = []
        for person in pairs:
            authors_and_papers[person] = []
    # Adds duplicate authors to authors_and_papers
    for duplicates in duplicate_authors.values():
        for person in duplicates:
            authors_and_papers[person] = []
    # Iterates through people in dict
    for person in authors_and_papers:
        # Iterates through papers 
        for paper in papers:
            # Checks if author is in the paper's authors
            if person in paper["authors"]:
                # Appends paper's doi to dict
                authors_and_papers[person].append(paper["DOI"])
                
    # Writes authors_and_papers to a file for usage in scrape_authors
    with open("./stored_authors/authors_and_papers.txt", "w") as aap_file:
        pprint(authors_and_papers, stream = aap_file)    
    # Authors not associated with any papers
    for author, papers in authors_and_papers.items():
        if len(papers) == 0:
            print(author)

def obtain_driver(url):
    """
    Opens the URL in a headless Firefox instance. 
    
    Parameters:
    url : string - URL of website to be opened
    
    Returns: a reference to the webdriver object
    """
    
    buttons = []
    driver_options = Options()
    driver_options.headless = True
    
    print("\n\n*****" + str(datetime.datetime.now()) + "*****")
    
    driver = webdriver.Firefox(options=driver_options, executable_path=GeckoDriverManager().install())
    
    # Needs to have the xpi in the current directory
    driver.install_addon(os.getcwd() + "/uBlock0@raymondhill.net.xpi", temporary=True)
    
    time.sleep(.5)
    
    return driver

def click_and_wait(driver, element, find_elements_by):
    """ 
    Clicks on element and waits for a page load. 
    
    Parameters:
    driver           : webdriver - existing webdriver
    element          : string    - string of the element to find (class or css_selector)
    find_elements_by : int       - searches element by: 0 for css_selector, 1 for class_name.
    
    Only works on an actual page load (will hang if the click only runs dynamic JS on the same webpage)
    """
    
    try:
        if find_elements_by == 0:
            button = driver.find_element_by_css_selector(element)
        else:
            button = driver.find_element_by_class_name(element)
            
        driver.execute_script("arguments[0].click()", button)
    except:
        print("No button")
        
    old_driver = driver.find_element_by_tag_name('html')

    WebDriverWait(driver, 10).until(EC.staleness_of(old_driver))
    
def search_paper(doi, driver, engine):
    """
    Searches for a paper's researchgate page.
    
    Parameters:
    doi    : string    - DOI of paper being searched
    driver : webdriver - Existing webdriver object
    engine : int       - Indicates which search engine to use (0 for Google, 1 for DuckduckGo)
    
    Returns: the associated webdriver.
    """
    
    print("\n---" + "New search " + str(datetime.datetime.now()) + "---")
    print("DOI: " + doi)
    
    if engine == 0:
        search_engine = "https://www.google.com"
        # Constructs the string being searched, randomizes it so it's not so robotic
        if random.randint(0, 1) == 0:
            query_string = '"' + doi + '"' + ' ' + '"researchgate.net"'
        else:
            query_string = '"researchgate.net"' + ' ' + '"' + doi + '"'
        query_string + " -filetype:pdf"
            
    elif engine == 1:
        search_engine = "https://duckduckgo.com/"
        query_string = '\\research gate' + ' ' + '"' + doi + '"'
    
    driver.get(search_engine)

    
    # Enters search string into searchbox
    if engine == 0:
        try: 
            blah = driver.find_element_by_xpath("/html/body/div/div[3]/form/div[2]/div/div[1]/div/div[1]/input")
        except NoSuchElementException: # Tries div[2]
            print("Trying second xpath")
            blah = driver.find_element_by_xpath("/html/body/div/div[3]/form/div[2]/div/div[1]/div/div[2]/input")
        
    
    elif engine == 1:
        blah = driver.find_element_by_xpath('//*[@id="search_form_input_homepage"]')
        
    blah.send_keys(query_string)
    
    
    time.sleep(random.randint(2, 7)) # to respect crawling
    
    if engine == 0:
        # Clicks on "I'm Feeling Lucky" button
        button = driver.find_element_by_xpath('//*[@id="gbqfbb"]')
        driver.execute_script("arguments[0].click()", button)
    elif engine == 1:
        blah.send_keys(Keys.RETURN)

    # Waits for page to load
    old_driver = driver.find_element_by_tag_name('html')
    WebDriverWait(driver, 10).until(EC.staleness_of(old_driver))
    time.sleep(2) # increased from .5 to 2 to respect crawling
    
    # Checks if paper was found
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    if "/sorry/" in driver.current_url:
        raise Exception("Captcha'd")
        
        return None
    elif "google.com" in driver.current_url:
        print("Paper not found")
        return None
    else:
        # Prints DOI string. Need to compare it to the actual doi to see if it's the correct paper.
        print("Success: found at " + str(driver.current_url))
        return driver

def show_authors(driver): 
    """
    Shows more authors on researchgate page by clicking on the show authors button
    
    Parameters:
    driver : webdriver - Existing webdriver that's already on the researchgate page of a paper
    
    Returns: the modified webdriver.
    """
    
    if not driver:
        print("Exiting: No driver")
        return None
    
    first_start = time.time()
    
    time.sleep(2) # Increase from .5 to 2 for stability
    
    try:
        button = driver.find_element_by_xpath("/html/body/div[2]/main/section/section[1]/div[2]/a")
        driver.execute_script("arguments[0].click()", button)
    except:
        print("No button")
        
    time.sleep(1) # Increased to 1 for stability
    
    first_end = time.time()

    print("DONE - " + str(first_end-first_start))
    
    return driver

def remove_chars(string):
    """
    Removes - and space characters from a string
    """
    
    return string.translate({ord(char): None for char in "- "})

def common_chars(string1, string2):
    """
    Counts the number of common characters in two strings ignoring case.
    
    Parameters:
    string1 : string
    string2 : string
    """
    
    common = Counter(string1.casefold()) & Counter(string2.casefold())
    return sum(common.values())

def compare_names(query_name, rg_name):
    """
    Compare names while agnostic to special characters and rearranged names
    
    Parameters:
    query_name : string - Name of the author as found in the database
    rg_name    : string - Name of the author as found on researchgate
    """
    
    # If one string is empty and not the other, return false
    if (query_name == "" and rg_name != "") or (query_name != "" and rg_name == ""):
        return False
    
    # Removes spaces and - from names
    query_clean = remove_chars(query_name)
    rg_clean = remove_chars(rg_name)
    
    # Same length and same amount of common characters
    return len(query_clean) <= len(rg_clean) and common_chars(query_clean, rg_clean) == len(query_clean)

def initial_check(name):
    """
    Checks if name is an initial, returns true if so
    
    Parameters:
    name : string
    """
    
    return (len(name) == 1) or ("." in name)

def compare_authors(query_author, rg_author):
    """
    Compares authors to see if they are the same person
    
    Parameters:
    query_author : list   - queried author's first name then last name
    rg_author    : string - researchgate author's full name (since it's not already tokenized when extracted)
    """
    
    # Checks if rg_author has any special non-ASCII characters. Translates query_author based on that and sets the author's first and last name strings.
    # Still doesn't address if one half of name uses UTF-8 only characters and the other half doesn't) but unlikely case
    if unidecode(rg_author) == rg_author:
        author_first = unidecode(query_author[0]).split()
        author_last = unidecode(query_author[2]).split()
    else:
        author_first = query_author[0].split()
        author_last = query_author[2].split()
    
    # Splits rg_author into tokens
    rg_tokens = rg_author.split()
    
    # Removes Jr from last name. Need to put the last check in case someone is just named "Jr"
    if len(rg_tokens) > 1 and rg_tokens[-1] == "Jr" or rg_tokens[-1] == "Jr.":
        rg_tokens.pop(-1)
    
    # Deals with no first_name in query_author
    if author_first == "" and compare_names(author_last, rg_tokens[-1]):
        return True
        
    # Incase rg_author uses first name initial, compares the first letter of queried author's first name to that string
    if initial_check(rg_tokens[0]):
        author_first[0] = str(author_first[0][0]) + "."
    
    # Merges first name for queried author
    merged_author_first = ""
    for name in author_first:
        
        # Incase rg_author uses first name initial, compares the first letter of queried author's first name to that string
        if initial_check(rg_tokens[0]):
            name = name[0] + "."
            
        merged_author_first = merged_author_first + name
        
    # Assigns last name to last part of last name
    author_last = author_last[-1]
    
    # Merges all but last name for researchgate name
    merged_rg_first = ""
    for name in rg_tokens[:-1]:
        
        # Adds periods to initials in the name
        if len(name) == 1:
            name = name + "."
        
        # Converts name to initial of queried author is in initial
        if initial_check(author_first[0]):
            name = name[0] + "."
        
        merged_rg_first = merged_rg_first + name
        
    return ( compare_names(merged_author_first, merged_rg_first) and author_last.casefold() == rg_tokens[-1].casefold() )
            
def soup_it(driver, author_tokens, pairing_dict, author_id):
    """
    Given the webdriver, parses its source for author URLs.
    
    Parameters:
    driver        : webdriver object - Existing webdriver that has already showed all authors on the researchgate page for a paper
    author_tokens : list             - List containing the searched author's name in tokens delimited by spaces
    pairing_dict  : dict             - To store the URLs into (for the respective author indicated by author_id)
    author_id     : int              - The searched author's id for usage in pairing_dict 
    
    Returns: the integer number of matches found on the page 
    """    
    
    time.sleep(1) # Increased to 1 for stability
      
    if driver is None:
        print("No soup for you: NO_PAPER")
        pairing_dict[author_id] = "NO_PAPER"
        return -1
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    thing = soup.find_all('div', {"class": "nova-v-person-list-item__title"})
    
    print("Searching for: " + str(author_tokens))
    
    match_count = 0
    answer = ""
    
    for stuff in thing:     
        author_name = stuff.find('a').string
        author_url = stuff.find('a').get("href")

        if compare_authors(author_tokens, author_name):
            print(str(author_url) + " <---------------- " + author_name)
            answer = author_url
            match_count += 1
        else:
            print(author_url + " ~ " + author_name)

    if match_count == 0:
        answer = "NOT_FOUND2"
    elif match_count > 1:
        answer = "Duplicates"
        
    print("Writing: " + answer)
    pairing_dict[author_id] = answer
        
    return match_count

def scrape_authors(search_engine):
    """
    Scrapes author URLs from researchgate and stores them to a dictionary.
    
    Parameters:
    search_engine : string - search engine URL to be used for scraping
    """
    
    original_file_descriptor = sys.stdout
    sys.stdout = open("./scraping_log.txt", "a")
    
    # Written from pairing_unknown_authors
    with open("./stored_authors/authors_and_papers.txt", encoding="utf8") as papers_file:
        authors_and_papers = eval(papers_file.read())
    with open("./stored_authors/authors_ids.txt", encoding="utf8") as authors_file:
        authors_ids = eval(authors_file.read())
    
    with open("./stored_authors/author_url_pairings.txt", encoding="utf8") as author_pair_file:
        authors_urls = eval(author_pair_file.read())

    # Any new entries not already saved in author_url_pairings.txt
    for author in authors_and_papers:
        if author not in authors_urls:
            authors_urls[author] = None

    if search_engine == "https://www.google.com":
        engine_number = 0
    elif search_engine == "https://duckduckgo.com/":
        engine_number = 1

    # replace_flag = "NOT_FOUND"
    replace_flag = None

    driver = obtain_driver(search_engine)
    time.sleep(2)

    for author in authors_urls:
        if authors_urls[author] == replace_flag: 
            # Author has no associated paper
            if len(authors_and_papers[author]) == 0:
                print("\n\nAUTHOR HAS NO PAPER")
                authors_urls[author] = "AUTHOR_HAS_NO_PAPER_IN_DATABASE"

                driver.quit()
                time.sleep(1)
                driver = obtain_driver(search_engine)
                time.sleep(2)

            else:
                success = soup_it(show_authors(search_paper(authors_and_papers[author][0], driver, engine_number)), authors_ids[author][:3], authors_urls, author)
                print(author)
                sys.stdout.flush()

                if success == -1 or success == 0:
                    driver.quit()
                    time.sleep(1)
                    driver = obtain_driver(search_engine)
                    time.sleep(2)

            time.sleep(random.randint(6, 12)) # Increased from 1 to 6-12 to respect crawling

    driver.quit()
    
    with open("./stored_authors/author_url_pairings.txt", "w") as dup_file:
        pprint(authors_urls, stream = dup_file)
        
    sys.stdout = original_file_descriptor
    
def comparing_scraped():
    """
    Compares scraped authors to each other to generate likely pairs.
    """
    
    with open("./stored_authors/author_url_pairings.txt", encoding="utf8") as pairings_file:
        author_url_pairings = eval(pairings_file.read())
    with open("./stored_authors/unknown_authors.txt", encoding="utf8") as unknowns_file:
        unknown_authors = eval(unknowns_file.read())
    with open("./stored_authors/duplicate_authors.txt", encoding="utf8") as duplicates_file:
        duplicate_authors = eval(duplicates_file.read())
    with open("./stored_authors/authors_ids.txt", encoding="utf8") as authors_ids_file:
        authors_ids = eval(authors_ids_file.read())
        
    # Used for reference when checking for authors in duplicate list
    unpacked_duplicates = set()
    for author_list in duplicate_authors.values():
        for author in author_list:
            unpacked_duplicates.add(author)
    sorted_unpacked_duplicates = sorted(list(unpacked_duplicates))
    
    h_likely = [] # Highly likely, unknowns that have matches
    possible = [] # Moderately likely, the ones whose possible matches have similar characters
    unlikely = [] # Unlikely, few matching characters
    
    # Pairs duplicates
    duplicate_pairing = {}
    for author, url in author_url_pairings.items():
        if author in sorted_unpacked_duplicates:
            duplicate_pairing[url] = []
    # Iterates through duplicates and appends pairings for each URL
    for author, pair in duplicate_authors.items():
        for pair_id in pair:
            duplicate_pairing[author_url_pairings[pair_id]].append(pair_id)
    merged_pairing = deepcopy(duplicate_pairing)
    # Generates list of all the url IDs for any urls that have them (i.e. urls with "contributions"
    url_num_list = []
    for url in duplicate_pairing:
        if "contributions" in url:
            url_num_list.append(re.search(r"\d+", url).group(0))
    # Generates list for all url IDs that have > 1 urls that contain them
    same_num_list = [num for num, count in Counter(url_num_list).items() if count > 1]
    
    # Iterates through nums then urls: longest_url -> longest (most complete name) to set as the new merged key
    # merged_entries -> merging of the values of the keys for assigning to the new merged key 
    for num in same_num_list:
        longest_url = ""        # Will be used as the key of the new merged entry (longer name is almost always the most detailed name)
        url_list = []           # Keeps track of urls to remove them from merged_pairing 
        merged_entries = []     # Used a value for new merged entry
        # Finds values and key for merging values
        for url in duplicate_pairing:
            if num in url:
                url_list.append(url)
                merged_entries += duplicate_pairing[url]
                # Assigns longest_url for use as a key
                if len(url) > len(longest_url):
                    longest_url = url
        # Merges/assigns values import itertools
        for url in url_list:
            if url == longest_url:
                merged_pairing[url] = merged_entries
            # Removes other unmerged entries
            else:
                merged_pairing.pop(url)
    # Iterates through merged_pairing. If there are any matches then append to highly likely list
    for url, matches in merged_pairing.items():
        if len(matches) > 1:
            h_likely.append(matches)
    
    # Pairs unknown names (e.g. first initial names)
    unknown_pairing = {}
    for unknown in unknown_authors:
        unknown_pairing[unknown] = None

    for author, pair in unknown_authors.items():
        if author in author_url_pairings:
            author_url = author_url_pairings[author]
        else:
            author_url = "no"

        found = "Unsure"
        for pair_id in pair:
            pair_url = author_url_pairings[pair_id]

            if "contributions" in author_url and "contributions" in pair_url:
                author_num = re.search(r"\d+", author_url).group(0)
                pair_num = re.search(r"\d+", pair_url).group(0)
                if author_num == pair_num:
                    found = pair_id
                    h_likely.append([author, pair_id])
            elif author_url ==  pair_url:
                found = pair_id
                h_likely.append([author, pair_id])
        unknown_pairing[author] = found
    
    all_h_likely_values = list(itertools.chain(*h_likely))
    h_likely_duplicates = [author for author, count in Counter(all_h_likely_values).items() if count > 1]
    
    # Selects an author as the "root" (the longest/one with the most special characters)
    processing_roots = {}
    root_names = {}
    # Iterates through the lists in h_likely
    for matches in h_likely:
        root_name = ""              # Longest/most accurate name to have everything merge into for database
        root_id = ""                # ID of the root author
        to_be_merged = deepcopy(matches) # remember to remove the root from matches
        # For every author_id in the matches list
        for author in matches: 
            full_name = authors_ids[author][0] + "_" + authors_ids[author][1] + "_" + authors_ids[author][2]
            if len(author) == 19: # i.e. if the author_id is an ORC ID since ORC IDs are 19 characters while regular ID hashes are 40 characters
                if root_id == "":
                    root_id = author
                else: # If there is a different ORC ID already (two different orc id == issue)
                    print(root_id + " " + author + "***** THESE ARE NOT THE SAME PERSON *****")
            if len(full_name) > len(root_name):
                root_name = full_name
                temp_id = author
        if root_id == "": 
            root_id = temp_id
        to_be_merged.remove(root_id)
        processing_roots[root_id] = to_be_merged
        root_names[root_id] = root_name

    with open("./stored_authors/root_names.txt", 'w') as root_out:
        pprint(root_names, stream = root_out)
    with open("./stored_authors/mergees.txt", 'w') as mergees_out:
        pprint(processing_roots, stream = mergees_out)

def select_and_print(cursor, command_string):
    """
    Selects entries from database and prints it out to the python interpreter. 
    
    Parameters: 
    cursor         : Sqlite cursor object - the sqlite3 cursor created from .cursor() on a connected sqlite 3 database
    command_string : String               - the entire select SQL command (e.g. "select * from testing123;")
    """
    
    cursor.execute(command_string)

    rows = cursor.fetchall()
    for row in rows:
        print(row.keys())

        string = ""
        for key in row.keys():
            string += str(row[key])
            string += " | "
        # print(str(row['test_1']) + " | " + str(row['test_2']))

        print(string)
        
    # print(rows.keys())
    
    # print(rows[0]['test_1'])
    # print(rows[0]['test_2'])
    print("---------------")
    
def update_values(cursor, root_id, mergee_id, new_root_name):
    """
    Updates values in a database by updating the root entry's name and merging the other entry into it
    
    Parameters:
    cursor        : MySQL cursor object - Existing MySQL cursor object
    root_id       : string              - ID of the author that should have its name changed
    mergee_id     : string              - ID of author that should be deleted and have its foreign keys redirected to the root_id
    new_root_name : string              - Name to be used to update root entry's name fields
    """
    
    # "root" would indicate no name change. Otherwise, update name fields for root author entry
    if new_root_name != "root":
        string_tokens = new_root_name.split('_')

        root_name_update = "update DBADSORPTION_SANDBOX.authors set given_name = '" + string_tokens[0] + "' where author_id = '" + root_id + "';"
        cursor.execute(root_name_update)

        root_name_update = "update DBADSORPTION_SANDBOX.authors set middle_name = '" + string_tokens[1] + "' where author_id = '" + root_id + "';"
        cursor.execute(root_name_update)

        root_name_update = "update DBADSORPTION_SANDBOX.authors set family_name = '" + string_tokens[2] + "' where author_id = '" + root_id + "';"
        cursor.execute(root_name_update)

    # Iterates through mergees and changes each foreign key in biblio_authors to the root_id 
    foreign_change_string = "update DBADSORPTION_SANDBOX.biblio_authors set author_id = '" + root_id + "' where author_id = '" +  mergee_id + "';"
    cursor.execute(foreign_change_string)
    
    delete_string = "DELETE from DBADSORPTION_SANDBOX.authors WHERE author_id = '" + mergee_id + "';"
    cursor.execute(delete_string)    
        
def sql_database_writer(username, password, database_name):
    """
    Main loop that iterates through mergees and updates them with update_values
    
    Parameters:
    username      : string - Username for logging into database
    password      : string - Password for logging into database
    database_name : string - Database name for making the connection
    """
    
    with open("./stored_authors/root_names.txt", 'r') as root_out:
        root_names = eval(root_out.read())
    with open("./stored_authors/mergees.txt", 'r') as mergees_out:
        mergees = eval(mergees_out.read())
    
    mariadb_connect = mariadb.connect(user=username, passwd=password, database=database_name)
    already_done_foreign = []
    for root, pair in mergees.items():

        for person in pair:
            already_done_foreign.append(person)

            if root not in already_done_foreign:
                update_values(cursor, root, person, root_names[root])