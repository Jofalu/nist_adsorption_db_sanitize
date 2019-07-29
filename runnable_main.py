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

import re
import itertools

import mysql.connector as mariadb

def authors2(host_name):
    # Loads the API calls, only need to do this once per run session

    # Loads the authors (and their IDs) to json
    # authors = json.load(urlopen("http://dirac.nist.gov/adsorption.nist.gov/isodb/api/authors.json"))
    authors = json.load(urllib.request.urlopen(host_name + "/adsorption.nist.gov/isodb/api/authors.json"))

    # Loads API call for papers
    # papers = json.load(urlopen("http://dirac.nist.gov/adsorption.nist.gov/isodb/api/minimalbiblio.json"))
    papers = json.load(urllib.request.urlopen(host_name + "/adsorption.nist.gov/isodb/api/minimalbiblio.json"))
    # Writes to file 
    with open("./stored_authors/papers.txt", "w") as papers_file:
        pprint(papers, stream = papers_file)
        
host_name = "http://pn108747.nist.gov:3680"