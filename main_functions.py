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
    # Loads the API calls, only need to do this once per run session

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
    Given a URL string, opens the URL in a headless Firefox instance. 
    
    Returns a reference to the webdriver object
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
    driver == webdriver
    element == string to find (class or css_selector)
    find_elements_by == integer: 0 for css_selector, 1 for class_name.
    
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
    Given a DOI, an existing driver, and an engine number (0 for Google, 1 for DDG), search for paper.
    
    Returns the associated webdriver.
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
    Given the webdriver, shows more authors. 
    
    Returns the modified webdriver.
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
    """Removes - and space characters from a string"""
    
    return string.translate({ord(char): None for char in "- "})

def common_chars(string1, string2):
    """Counts the number of common characters in two strings"""
    
    common = Counter(string1.casefold()) & Counter(string2.casefold())
    return sum(common.values())

def compare_names(query_name, rg_name):
    """Compare names while agnostic to special characters and rearranged names"""
    
    # If one string is empty and not the other, return false
    if (query_name == "" and rg_name != "") or (query_name != "" and rg_name == ""):
        return False
    
    # Removes spaces and - from names
    query_clean = remove_chars(query_name)
    rg_clean = remove_chars(rg_name)
    
    # Same length and same amount of common characters
    return len(query_clean) <= len(rg_clean) and common_chars(query_clean, rg_clean) == len(query_clean)

def initial_check(name):
    """Checks if name is an initial, returns true if so"""
    
    return (len(name) == 1) or ("." in name)

def compare_authors(query_author, rg_author):
    """
    Compares authors
    
    Parameters:
    query_author : list of of queried author's first name then last name
    rg_author    : string of researchgate author's full name
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
    driver == webdriver
    author_tokens == list containing the searched author's name in tokens delimited by spaces
    pairing_dict == Dictionary to store the URLs into (for the respective author indicated by author_id)
    author_id == The searched author's id for usage in pairing_dict 
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
    

    
def test():
    print("test")