# Import the required packages/modules

from __future__ import division, unicode_literals 
from bs4 import BeautifulSoup
from datetime import datetime
from IPython.display import clear_output
from time import sleep
import pandas as pd
import codecs
import requests
import re
import numpy as np
import itertools

# Create the Court class
class Court:

    def __init__(self, name):
        """
        Create a court. Only accepts "subordinate" and "supreme".
        """
        # Set the name of the instance
        self.name = name
        
        # Raise an error if the user tries to create an instance of a court that does not exist
        if self.name != 'subordinate' and self.name != 'supreme':
            raise CourtNameError("There is only the Subordinate (State) or Supreme Court!")

    def __set_soup(self):
        """
        Sets the target Court's Lawnet page using `name`.
        """
        # Set the url for API requests
        self.url = "https://www.lawnet.sg/lawnet/web/lawnet/free-resources?p_p_id=freeresources_WAR_lawnet3baseportlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_pos=2&p_p_col_count=3&_freeresources_WAR_lawnet3baseportlet_action="+self.name
        
        # Set the variables for BeautifulSoup parsing
        self.response = requests.get(self.url)
        self.html = self.response.text
        self.court = BeautifulSoup(self.html, 'lxml')

    def __get_num_pages(self):
        """
        Fetches number of pages from the website as an int
        """
        # Check for the last page from the html code
        self.page = str(self.court.find_all('li', {'class': 'lastPageActive'}))
        self.page = ''.join(filter(str.isdigit, self.page))
        
        # Replace the first "3" as it comes from the url
        self.last_page = int(self.page.replace("3","",1))

    def __fetch_urls(self):
        """
        Uses `name` to scrape lawnet for the cases and urls and store it in a dataframe `court_df`.
        """
        # Create an empty list for results
        self.results_list = []
        
        # Set the base domain for the urls
        self.domain = "https://www.lawnet.sg/lawnet/web/lawnet/free-resources?p_p_id=freeresources_WAR_lawnet3baseportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_pos=2&p_p_col_count=3&_freeresources_WAR_lawnet3baseportlet_action=openContentPage&_freeresources_WAR_lawnet3baseportlet_docId="
        
        # Create counter for current page
        self.current_page = 1
        
        # Loop while it is not the last page
        while self.current_page <= self.last_page:
            
            # Set the full url for the current page
            url1 = self.url+"&_freeresources_WAR_lawnet3baseportlet_page="+str(self.current_page)
            
            # Establishing the connection to the web page:
            response1 = requests.get(url1)
            
            # Pull the HTML string out of requests and convert it to a Python string.
            html1 = response1.text
            court1 = BeautifulSoup(html1, 'lxml')
            
            # Get the relevant elements (date, name, link)
            search_results = court1.find_all('ul', {'class': 'searchResultsHolder'})
            
            # Iterate throught the search results to find the list elements
            for li in search_results:
                li_list = li.find_all('li')
                for element in li_list:
                   # start a dictionary to store this item's data
                    result = {}
                    
                    # Set the court
                    result['court'] = self.name
                    
                    # get the date
                    result['date'] = element.find('p', {'class': 'resultsDate'}).text
                    
                    # get the title and full link/url
                    a_href = element.find('a')
                    if a_href:
                        result['title'] = a_href.text.strip()   # element text
                        link = str(a_href['href']) # href link
                        
                        # Remove unnecessary parts of the link
                        link = link.replace("javascript:viewContent","")
                        link = link.strip("')(")
                        
                        # Add the result including the domain
                        result['link'] = self.domain+link
                        
                        # only store "full" rows of data
                        if len(result) == 4:
                            self.results_list.append(result)
                            
                    # Clear cell output
                    clear_output(wait=True)

                    # Print current progress
                    print(f'Current progress: page {self.current_page}/{self.last_page}.')

            # Raise page counter for the loop to pull results from the next page
            self.current_page += 1
            
        # Create a dataframe with all the links, sorted by date
        self.court_df = pd.DataFrame(self.results_list)
        self.court_df = self.court_df.sort_values(by='date')
        self.court_df = self.court_df.reset_index(drop=True)
        
        # Print current progress
        print(f'Current progress: DataFrame created.')

    def __only_crim(self):
        """
        Narrows results to only Criminal cases
        """
        # Filters to cases where "Public Prosecutor" is mentioned - these are criminal cases
        self.court_df = self.court_df[self.court_df['title'].str.contains("Public Prosecutor")]
        self.court_df = self.court_df.reset_index(drop=True)

        # Print current progress
        print(f'Current progress: Narrowed to only Criminal cases.')

    def __compare_csv(self):
        """
        Loads the complete csv database and compares data with the dataframe to identify new entries.
        Returns new entries as `court_df` and all entries as `court_full`.
        """
        # Convert dates to datetime
        self.court_df['date'] = pd.to_datetime(self.court_df['date'], dayfirst=True)
        
        # Load the full dataset .csv and convert dates to datetime
        self.court_full = pd.read_csv(f'../data/{self.name}court_compiled.csv')
        self.court_full['date'] = pd.to_datetime(self.court_full['date'], format='%Y-%m-%d')
        
        # Filter to entries which are not in the full dataset
        self.court_df = self.court_df[~self.court_df['link'].isin(self.court_full['link'])]
        
        # Merge new entries to the full dataset, sorted by date
        self.court_full = self.court_full.merge(self.court_df, how='outer')
        self.court_full = self.court_full.sort_values(by='date')
        self.court_full = self.court_full.reset_index(drop=True)


        # Print current progress
        print(f'Current progress: {len(self.court_df.date)} New entries identified and saved.')

    def __export_csv(self):
        """
        Exports dataframes to the respective .csv files
        """
        # Save the new entries in a .csv
        self.court_df.to_csv(path_or_buf=f'../data/{self.name}court.csv', index=False)
        
        # Save the new full dataset in a .csv
        self.court_full.to_csv(path_or_buf=f'../data/{self.name}court_compiled.csv', index=False)

    def pull_urls(self):
        """
        Call command to pull urls and export to csv database
        """
        # Call the functions required to pull the urls from Lawnet
        self.__set_soup()
        self.__get_num_pages()
        self.__fetch_urls()
        self.__only_crim()
        self.__compare_csv()
        self.__export_csv()
        
        # Write a log of the last pull date
        self.file = open('../logs/pull_log.txt', 'a', encoding='utf_8')
        self.file.write(f'list last updated on: {datetime.today()}; \n')
        
        # Print current progress
        print(f'Current progress: Completed url pull and export.')

    def load_csv(self):
        """
        Loads .csvs using `name` as lists of dictionaries.
        """
        # Load the .csv files as pandas dataframes
        self.court_link_list = [pd.read_csv(f'../data/{self.name}court.csv').link.to_dict()]
        self.court_link_dict = pd.read_csv(f'../data/{self.name}court_compiled.csv').link.to_dict()
        self.court_full = pd.read_csv(f'../data/{self.name}court_compiled.csv')
        self.court_full['date'] = pd.to_datetime(self.court_full['date'], format='%Y-%m-%d')

    def __save_html(self):
        """
        Iterates through the lists of dictionaries to save judgments from Lawnet as a .html file.
        """
        # Create a counter for the progress bar
        self.count = 1

        # Sets the file name for the judgment
        self.file_name = self.name+'court'
            
        # Iterate through the list of new link entries
        for item in self.court_link_list:
            for key, value in item.items():            
                # Sets the request for the link
                url = value
                response = requests.get(url)
                
                # Pull the HTML string out of requests and convert it to a Python string.
                html = response.text
                soup = BeautifulSoup(html, 'lxml')
                
                # Match value to key in full list for file name
                key1 = list(self.court_link_dict.keys())[list(self.court_link_dict.values()).index(value)]
                try:                    
                    # Try to save as html file
                    file = open(f'../judgments/{self.name}_court/{self.file_name}_{key1}.html', 'x', encoding='utf_8')
                    file.write(str(soup))
                    file.close
                    sleep(randint(1,4))

                    # Clear cell output
                    clear_output(wait=True)

                    # Print current progress
                    print(f'Current progress: {self.count}/{len(self.court_link_list[0])}.')
                    self.count += 1

                except:
                    # Skip if error, print an error log with index
                    file = open('../logs/error_log.txt', 'a', encoding='utf_8')
                    file.write(f'{self.file_name}_list error: {key1}.html : {datetime.today()}; \n')
                    
                    # Clear cell output
                    clear_output(wait=True)

                    # Print current progress
                    print(f'Current progress: {self.count}/{len(self.court_link_list[0])}.')
                    self.count += 1

    def archive(self):
        """
        Call command to archive the urls as .html files.
        """
        # Call the functions required to archive the new html files from Lawnet
        self.load_csv()
        self.__save_html()
        
        # Update the log file for the last archival date
        self.file = open('../logs/archival_log.txt', 'a', encoding='utf_8')
        self.file.write(f'last archived on: {datetime.today()}; \n')
        
        # Print current progress
        print(f'Current progress: {len(self.court_link_list[0])} HTMLs archived.')
        
# Create a class for the database creation / updating
class Database:

    def __init__(self):
        """
        Initializes the class and loads the datasets.
        """
        # Load the .csv files as pandas dataframes
        self.supremecourt_df = pd.read_csv('../data/supremecourt_compiled.csv')
        self.subordinatecourt_df = pd.read_csv('../data/subordinatecourt_compiled.csv')
        self.database_df = pd.read_csv('../data/database.csv')
        self.statutes_df = pd.read_csv('../data/statutes_crimes.csv')
        
    def __get_num_rows(self):
        """
        Calculates the number of rows there are in each dataset.
        """
        # Find the number of rows in each court's dataframe
        self.__supremecourt_rows = len(self.supremecourt_df)
        self.__subordinatecourt_rows = len(self.subordinatecourt_df)
        
        # Compare the number of rows for each court in the database to find out how many new rows there are
        self.__new_supremecourt_rows = self.__supremecourt_rows - len(self.database_df[self.database_df['court_tag'] == 'supreme'])
        self.__new_subordinatecourt_rows = self.__subordinatecourt_rows - len(self.database_df[self.database_df['court_tag'] == 'subordinate'])

    def __get_case_name(self):
        """
        Takes out the case name from the judgment
        """
        # Search for the case name in the judgment
        self.__case_name = {'case_name': self.__search_results.find('h2').text.strip()}
        
        # Create a temp variable for the case name without the case citation notation by looking for patterns of Capitalized words with name terms which are followed by v and further capitalized words with name terms as these suggest that it is a case name
        self.__temp_case_name = re.search('(([A-Z][a-z]*)(([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))* v (([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))*(?=|))', str(self.__case_name)).group(0).strip()
        
        # Return case name as a dictionary
        return self.__case_name
    
    def __get_court(self):
        """
        Takes out the court name from the judgment
        """
        # Search for the info table in the html
        self.__temp_results1 = self.__search_results.find('table', {'id': 'info-table'})
        
        # Picks out the court info in the search results as string
        self.__temp_court = re.search('Tribunal/Court : (\w* )*(?=Coram)', self.__temp_results1.text).group(0).strip()
        
        # Split the court info string to the key and value
        self.__temp_list = self.__temp_court.split(" : ")
        
        # Set court info in a dictionary
        self.__court = {str.lower(self.__temp_list[0]): self.__temp_list[1]}
        
        # Return court info as a dictionary
        return self.__court
                        
    def __get_date(self):
        """
        Takes out the court name from the judgment
        """
        # Search for the info table in the html
        self.__temp_results1 = self.__search_results.find('table', {'id': 'info-table'})
        
        # Picks out the decision date in the search results as string
        self.__temp_date = re.search('Decision Date : (\w* )*(?=Tribunal)', self.__temp_results1.text).group(0).strip()
        
        # Split the decision date to the key and value
        self.__temp_list = self.__temp_date.split(" : ")
        
        # Set decision date in a dictionary
        self.__decision_date = {'decision_date': self.__temp_list[1]}
        
        # Return decision date as a dictionary
        return self.__decision_date
        
    def __get_statute(self):
        """
        Identifies criminal offences and statutes mentioned in the judgment based on its header as a first choice, and text as a second choice.
        """
        # Create an empty list of offences
        self.__offences = []
        
        # First try to identify the crimes based on the header of the judgment.
        try:
            # Search for the header in the html
            self.__temp_results1 = self.__search_results.find('p', {'class': 'txt-body'})
            self.__temp_results2 = self.__temp_results1.find_all('span')
            
            # Iterate through the results and try to find the offences
            for result in self.__temp_results2:
                try:
                    # Search for "Section(s) or "s(s)" (abbreviated sections) with digits. First replace weird text.
                    section = re.search('([Ss](ection|)(s|) \d+)', result.text.replace('\xa0',' ')).group(0).strip()
                    
                    # Pick out only the section numbers
                    section_num = re.sub('([Ss](ection|)(s|) )', "", section)
                    
                    # Pick out patterns which end in Act or Code as these refer to statutes
                    statute = re.search(r'((([A-Z][a-z]*)|(Corruption, Drug Trafficking and Other Serious Crimes \(Confiscation of Benefits\)|and|of| )){2,}(Act|Code))', result.text.replace('\xa0',' ')).group(0).strip()
                    
                    # Combine section numbers and statute
                    section_statute = section_num + " " + statute
                    
                    # Checks the database of statutes I created to find a possible offence if it exists within and adds it to the list of offences for this judgment
                    if section_statute in self.statutes_df['section_statute'].values:
                        index = self.statutes_df[self.statutes_df['section_statute'] == section_statute].index
                        offence = self.statutes_df.iloc[index].values
                        self.__offences.append([offence[0][1], section_statute])
                        
                    # If not found within the database of statutes, adds the section number and statute but list offences as "unsure"
                    else:
                        self.__offences.append(['Not in database', section_statute])
                        
                except:
                    pass
        except:
            pass
        
        # If the judgment header does not contain the section and statute, identify it through the text
        if len(self.__offences) == 0:
            print('No offences found in header, checking document text..')
            
            # Instantiate empty lists
            offence_b = []
            sections_found = []
            statutes_found = []
            
            # Search for all the document text
            self.__search_results2 = self.__search_results.text.replace("\xa0"," ")
            
            # Instantiate empty lists
            section_list = []
            statute_list = []
            try:
                # Try to find the sections as above
                sections = re.findall('( [Ss](ection|)(s|) \d+)', self.__search_results2)

                # If sections is not empty:
                if sections != []:
                    # Iterate through the sections and adds their digits to the section list
                    for s in sections:
                        section_list.append(re.findall(r'\d+',s[0]))

                        # Add the sections found to the list
                        for ss in section_list:
                            sections_found.append(ss[0])

                # Try to find the statutes as above
                statutes = re.findall(r'((([A-Z][a-z]*)|(Corruption, Drug Trafficking and Other Serious Crimes \(Confiscation of Benefits\)|and|of| )){2,}(Act|Code))', self.__search_results2)

                # If statutes is not empty:
                if statutes != []:
                    # Iterate through the statutes and adds their name to the statute list
                    for s in statutes:
                        statute_list.append(s[0].strip())

                        # Add the statutes found to the list
                        for ss in list(statute_list):
                            statutes_found.append(ss)
            except:
                pass
            
            if statutes_found != []:
                # Convert the sections and statutes found to sets to remove duplicates
                sections2 = set(sections_found)
                statutes2 = set(statutes_found)
                
                # Permutate through the sections and statutes to find all possible combinations of the two
                combinations = list(itertools.product(list(sections2),list(statutes2)))
                
                # Check if combinations is blank
                if combinations == []:
                    combinations = list(statutes_found)
                
                # Instantiate list of possible offences
                possible_offences = []
                
                # Check if combinations has only 1 entry and sets possible_offences as combinations
                if type(combinations[0]) == str:
                    possible_offences = combinations
                
                else:
                    # Add each possible offence from the permutations to the list of possible offences
                    for offence in combinations:
                        possible_offences.append(' '.join(offence))
                    
                # Check the database of statutes I created to find a possible offence if it exists within and adds it to the list of offences for this judgment
                for value in possible_offences:
                    if value in self.statutes_df['section_statute'].values:
                        index = self.statutes_df[self.statutes_df['section_statute'] == value].index
                        offence = self.statutes_df.iloc[index].values
                        offence_b.append([offence[0][1], value])
                        [self.__offences.append(x) for x in offence_b if x not in self.__offences];
                        
                    # If not found within the database of statutes, adds the section number and statute but list offences as "unsure"
                    else:
                        offence_b.append(['Not in database', value])
                        [self.__offences.append(x) for x in offence_b if x not in self.__offences];
            
        # Instantiate empty lists and dictionaries
        self.__title = []
        self.__temp_title = []
        self.__statute = []
        self.__title_statute = {}
        
        # Iterate through self.__offences
        for item in self.__offences:
        # Add each offence into temp_title and statute
            self.__temp_title.append(item[0])
            self.__statute.append(item[1])
            
        # converts temp_title to a set to remove duplicates
        self.__temp_title = set(self.__temp_title)
        
        # Adds each temp_title to title
        for titles in self.__temp_title:
            self.__title.append(str(titles))
            
        # Joins all the titles in title list as a full string
        self.__title = ",".join(self.__title)
        
        # Joins all the statutes in statute list as a full string
        self.__statute = ",".join(self.__statute)
        
        # Returns title and statute as a dictionary
        self.__title_statute = {'possible_titles': self.__title, 'possible_statutes': self.__statute}
        return self.__title_statute
     
    def __get_citations(self):
        """
        Searches the document text for case citations which are in the format of `____ v ____`.
        """
        # Replaces weird characters from html and return text
        self.__judgment_text = self.__search_results.text.replace('\xa0','')
        
        # Searches through text for patterns of Capitalized words with name terms which are followed by v and further capitalized words with name terms as these suggest that it is a case name
        self.__case_search = re.findall('(([A-Z][a-z]*)(([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))* v (([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))*(?=|))', self.__judgment_text)
        
        # Instantiate an empty list
        self.__cases = []
        
        # Iterate through the results to append the case name into a list, excluding duplicates
        for item in self.__case_search:
            case = []
            temp_case = re.search('(([A-Z][a-z]*)(([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))* v (([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))*(?=|))', str(item)).group(0).replace("In ","").strip()
            
            # Try removing a few wrong words which are captured
            try:
                temp_case = temp_case.replace('Antecedents','').replace('Untraced','').strip()
            except:
                pass
            # Append temp_case to the list of cases
            case.append(temp_case)
            
            # Append to self.__cases if not a duplicate
            [self.__cases.append(x) for x in case if x not in self.__cases];
            
        # Remove this judgment's name from the list as it cannot be its own citation
        self.__cases.remove(self.__temp_case_name)
        
        # Change the list to a string
        self.__cases = ",".join(self.__cases)
        
        # Returns the citations as a dictionary
        self.__citations = {'citations': self.__cases}
        return self.__citations
            
    def __get_miscellaneous(self):
        """
        Searches the document text to identify if mitigating factors were discussed, and if aggravating factors were discussed
        """
        # Searches the judgment text to see if mitigation or mitigating is mentioned and returns 1 for yes, 0 for no
        if re.search(r'[mM]itigation|[mM]itigating',self.__judgment_text):
            self.__mitigation_discussed = 1
        else:
            self.__mitigation_discussed = 0
            
        # Searches the judgment text to see if aggravating or aggravated is mentioned and returns 1 for yes, 0 for no
        if re.search(r'[aA]ggravating|[aA]ggravated',self.__judgment_text):
            self.__aggravated_discussed = 1
        else:
            self.__aggravated_discussed = 0   
            
        # Returns the results as a dictionary
        self.__miscellaneous = {'mitigation_discussed': self.__mitigation_discussed, 'aggravation_discussed': self.__aggravated_discussed}
        return self.__miscellaneous
        
        
    def __process_judgments(self, court):
        """
        Loads each new html judgment and performs the NLP steps to extract the key information.
        """
        # Instantiate a list for the dictionary outputs of the above functions
        self.dictionaries_list = []
        
        # Set a default start value
        self.__start = 0
        
        # Check which court is being processed, and find the number of new rows to set the start and end indices
        if court == 'supreme':
            self.__start = self.__supremecourt_rows - self.__new_supremecourt_rows
            self.__end = self.__supremecourt_rows
        elif court == 'subordinate':
            self.__start = self.__subordinatecourt_rows - self.__new_subordinatecourt_rows
            self.__end = self.__subordinatecourt_rows
            
        # Raise an error if an invalid court is set
        else:
            raise CourtNameError("There is only the Subordinate (State) or Supreme Court!")
            
        # Load the dataset based on which court is given
        self.dataset = pd.read_csv(f'../data/{court}court_compiled.csv')
        
        # Check if there are any new entries
        if self.__start < self.__end:
            # Create index range for new entries and iterate through the range of indices
            for index in range(self.__start, self.__end):               
                # Set the case_link to be the link for the current index
                self.__case_link = self.dataset.loc[index]['link']
                
                # Print the current progress
                print(f'Current progress: {index+1}/{self.__end}.')
                
                # Load the judgment html for the current index and parse it in BeautifulSoup
                load_judgment = codecs.open(f'../judgments/{court}_court/{court}court_{index}.html', 'r', 'utf-8')
                print('Judgment loaded')
                self.document = BeautifulSoup(load_judgment.read())
                print('BeautifulSoup initialized')
                
                # Create __search_results which are the contents of the html
                self.__search_results = self.document.find('div', {'class': 'contentsOfFile'})
                print('Judgment text identified')
                
                # Call the functions above to extract the information required
                self.__get_case_name()    
                print(f'Case name extracted: {self.__case_name}')
                self.__get_court()
                print(f'Court extracted: {self.__court}')
                self.__get_date()       
                print(f'Decision date extracted: {self.__decision_date}')
                self.__get_statute()   
                print(f'Statutes extracted*: {self.__title_statute}')
                self.__get_citations()      
                print(f'Citations extracted*: {self.__citations}')
                self.__get_miscellaneous()
                print(f'Miscellaneous extracted*: {self.__miscellaneous}')
                
                # Add a court_tag column which specifies whether it is subordinate or supreme court (for the identification of new entries)
                self.__court_column = {'court_tag': court}
                print('tag set')
                
                # Add the case url
                self.__add_link = {'link': self.__case_link}
                print('case link set')
                
                # Create and merge a dictionary which merges all the information extracted for each judgment
                self.__dictionaries_merged = self.__case_name.copy()
                self.__dictionaries_merged.update(self.__court)
                self.__dictionaries_merged.update(self.__decision_date)
                self.__dictionaries_merged.update(self.__title_statute)
                self.__dictionaries_merged.update(self.__citations)
                self.__dictionaries_merged.update(self.__miscellaneous)
                self.__dictionaries_merged.update(self.__court_column) 
                self.__dictionaries_merged.update(self.__add_link)
                
                # Add the dictionary for each judgment into a list of dictionaries
                self.dictionaries_list.append(self.__dictionaries_merged)

                # Clear cell output
                clear_output(wait=True)
            
            # Create a Dataframe out of the list of dictionaries
            self.database = pd.DataFrame(self.dictionaries_list)
            
            # Print current progress
            print(f'Current progress: DataFrame created.')
            
            # Merge the Dataframe into the full database
            self.database_df = self.database_df.merge(self.database, how='outer')
            self.database_df.reset_index(drop=True)
            
        # Print 'No new entries' if there are no new entries.
        else:
            self.database = pd.DataFrame()
            print('No new entries')
            

    def __export_database(self):
        """
        Exports dataframes to the respective .csv files
        """
        # Save the temporary database and updated full database to .csv files
        self.database.to_csv(path_or_buf=f'../data/database_temp.csv', index=False)
        self.database_df.to_csv(path_or_buf=f'../data/database.csv', index=False)

    def create_database(self,court):
        """
        Call command to pull urls and export to csv database
        """
        # Call the functions to create / update the database
        self.__get_num_rows()
        self.__process_judgments(court)
        self.__export_database()
        
        # Update the log file for the latest database update date
        self.file = open('../logs/database_log.txt', 'a', encoding='utf_8')
        self.file.write(f'database last updated on: {datetime.today()}; \n')
        
        # Print current progress
        print(f'Current progress: Completed judgment processing and export.')
        
# Create a class for exceptions
class CourtNameError(Exception):
    pass
