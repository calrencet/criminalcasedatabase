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


class Court:

    def __init__(self, name):
        """
        Create a court. Only accepts "subordinate" and "supreme".
        """
        self.name = name
        if self.name != 'subordinate' and self.name != 'supreme':
            raise CourtNameError("There is only the Subordinate (State) or Supreme Court!")

    def __set_soup(self):
        """
        Sets the target Court's Lawnet page using `name`.
        """
        self.url = "https://www.lawnet.sg/lawnet/web/lawnet/free-resources?p_p_id=freeresources_WAR_lawnet3baseportlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_pos=2&p_p_col_count=3&_freeresources_WAR_lawnet3baseportlet_action="+self.name
        self.response = requests.get(self.url)
        self.html = self.response.text
        self.court = BeautifulSoup(self.html, 'lxml')

    def __get_num_pages(self):
        """
        Fetches number of pages from the website as an int
        """
        self.page = str(self.court.find_all('li', {'class': 'lastPageActive'}))
        self.page = ''.join(filter(str.isdigit, self.page))
        # Replace the first "3" as it comes from the url
        self.last_page = int(self.page.replace("3","",1))

    def __fetch_urls(self):
        """
        Uses `name` to scrape lawnet for the cases and urls and store it in a dataframe `court_df`.
        """
        self.results_list = []
        self.domain = "https://www.lawnet.sg/lawnet/web/lawnet/free-resources?p_p_id=freeresources_WAR_lawnet3baseportlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_pos=2&p_p_col_count=3&_freeresources_WAR_lawnet3baseportlet_action=openContentPage&_freeresources_WAR_lawnet3baseportlet_docId="
        # Create counter for current page
        self.current_page = 1
        # Loop while it is not the last page
        while self.current_page <= self.last_page:
            url1 = self.url+"&_freeresources_WAR_lawnet3baseportlet_page="+str(self.current_page)
            # Establishing the connection to the web page:
            response1 = requests.get(url1)
            # Pull the HTML string out of requests and convert it to a Python string.
            html1 = response1.text
            court1 = BeautifulSoup(html1, 'lxml')
            # Get the relevant elements (date, name, link)
            search_results = court1.find_all('ul', {'class': 'searchResultsHolder'})
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
                        link = link.replace("javascript:viewContent","")
                        link = link.strip("')(")
                        result['link'] = self.domain+link
                    # only store "full" rows of data
                        if len(result) == 4:
                            self.results_list.append(result)
                    # Clear cell output
                    clear_output(wait=True)

                    # Print current progress
                    print(f'Current progress: page {self.current_page}/{self.last_page}.')

            # Raise page counter
            self.current_page += 1
        self.court_df = pd.DataFrame(self.results_list)
        self.court_df = self.court_df.sort_values(by='date')
        self.court_df = self.court_df.reset_index(drop=True)
        # Print current progress
        print(f'Current progress: DataFrame created.')

    def __only_crim(self):
        """
        Narrows results to only Criminal cases
        """
        self.court_df = self.court_df[self.court_df['title'].str.contains("Public Prosecutor")]
        self.court_df = self.court_df.reset_index(drop=True)

        # Print current progress
        print(f'Current progress: Narrowed to only Criminal cases.')

    def __compare_csv(self):
        """
        Loads the complete csv database and compares data with the dataframe to identify new entries.
        Returns new entries as `court_df` and all entries as `court_full`.
        """
        self.court_df['date'] = pd.to_datetime(self.court_df['date'], dayfirst=True)
        self.court_full = pd.read_csv(f'../data/{self.name}court_compiled.csv')
        self.court_full['date'] = pd.to_datetime(self.court_full['date'], format='%Y-%m-%d')
        self.court_df = self.court_df[~self.court_df['link'].isin(self.court_full['link'])]
        self.court_full = self.court_full.merge(self.court_df, how='outer')
        self.court_full = self.court_full.sort_values(by='date')
        self.court_full = self.court_full.reset_index(drop=True)


        # Print current progress
        print(f'Current progress: {len(self.court_df.date)} New entries identified and saved.')

    def __export_csv(self):
        """
        Exports dataframes to the respective .csv files
        """
        self.court_df.to_csv(path_or_buf=f'../data/{self.name}court.csv', index=False)
        self.court_full.to_csv(path_or_buf=f'../data/{self.name}court_compiled.csv', index=False)

    def pull_urls(self):
        """
        Call command to pull urls and export to csv database
        """
        self.__set_soup()
        self.__get_num_pages()
        self.__fetch_urls()
        self.__only_crim()
        self.__compare_csv()
        self.__export_csv()
        self.file = open('../logs/pull_log.txt', 'a', encoding='utf_8')
        self.file.write(f'list last updated on: {datetime.today()}; \n')
        # Print current progress
        print(f'Current progress: Completed url pull and export.')

    def load_csv(self):
        """
        Loads .csvs using `name` as lists of dictionaries.
        """
        self.court_link_list = [pd.read_csv(f'../data/{self.name}court.csv').link.to_dict()]
        self.court_link_dict = pd.read_csv(f'../data/{self.name}court_compiled.csv').link.to_dict()
        self.court_full = pd.read_csv(f'../data/{self.name}court_compiled.csv')
        self.court_full['date'] = pd.to_datetime(self.court_full['date'], format='%Y-%m-%d')

    def __set_file_name(self):
        """
        Sets the file name for the judgment.
        """
        self.file_name = self.name+'court'

    def __save_html(self):
        """
        Iterates through the lists of dictionaries to save judgments from Lawnet as a .html file.
        """
        self.count = 1
        for item in self.court_link_list:
            for key, value in item.items():
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

    def archive(self):
        """
        Call command to archive the urls as .html files.
        """
        self.load_csv()
        self.__set_file_name()
        self.__save_html()
        self.file = open('../logs/archival_log.txt', 'a', encoding='utf_8')
        self.file.write(f'last archived on: {datetime.today()}; \n')
        # Print current progress
        print(f'Current progress: {len(self.court_link_list[0])} HTMLs archived.')
        

class Database:

    def __init__(self):
        """
        Initializes the class and loads the datasets.
        """
        self.courts = ['subordinate', 'supreme']
        self.supremecourt_df = pd.read_csv('../data/supremecourt_compiled.csv')
        self.subordinatecourt_df = pd.read_csv('../data/subordinatecourt_compiled.csv')
        self.database_df = pd.read_csv('../data/database.csv')
        self.statutes_df = pd.read_csv('../data/statutes_crimes.csv')
        
    def __get_num_rows(self):
        """
        Calculates the number of rows there are in each dataset.
        """
        self.__supremecourt_rows = len(self.supremecourt_df)
        self.__subordinatecourt_rows = len(self.subordinatecourt_df)
        self.__new_supremecourt_rows = self.__supremecourt_rows - len(self.database_df[self.database_df['court'] == 'supreme'])
        self.__new_subordinatecourt_rows = self.__subordinatecourt_rows - len(self.database_df[self.database_df['court'] == 'subordinate'])

    def __get_case_name(self):
        """
        Takes out the case name from the judgment
        """
        self.__case_name = {'case_name': self.__search_results.find('h2').text.strip()}
        self.__temp_case_name = re.search('((([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))* v (([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))*(?=|))', str(self.__case_name)).group(0).strip()
        return self.__case_name
    
    def __get_court(self):
        """
        Takes out the court name from the judgment
        """
        self.__temp_results1 = self.__search_results.find('table', {'id': 'info-table'})
        self.__temp_court = re.search('Tribunal/Court : (\w* )*(?=Coram)', self.__temp_results1.text).group(0).strip()
        self.__temp_list = self.__temp_court.split(" : ")
        self.__court = {str.lower(self.__temp_list[0]): self.__temp_list[1]}
        return self.__court
                        
    def __get_date(self):
        """
        Takes out the court name from the judgment
        """
        self.__temp_results1 = self.__search_results.find('table', {'id': 'info-table'})
        self.__temp_date = re.search('Decision Date : (\w* )*(?=Tribunal)', self.__temp_results1.text).group(0).strip()
        self.__temp_list = self.__temp_date.split(" : ")
        self.__decision_date = {str.lower(self.__temp_list[0]): self.__temp_list[1]}
        return self.__decision_date
        
    def __get_statute(self):
        """
        Identifies criminal offences and statutes mentioned in the judgment based on its header as a first choice, and text as a second choice.
        """
        self.__offences = []
        # First try to identify the crimes based on the header of the judgment.
        try:
            self.__temp_results1 = self.__search_results.find('p', {'class': 'txt-body'})
            self.__temp_results2 = self.__temp_results1.find_all('span')
            for result in self.__temp_results2:
                try:
                    section = re.search('([Ss](ection|)(s|) \d+)', result.text.replace('\xa0',' ')).group(0).strip()
                    section_num = re.sub('([Ss](ection|)(s|) )', "", section)
                    statute = re.search(r'((([A-Z][a-z]*)|(of| )*)*(Act|Code))', result.text.replace('\xa0',' ')).group(0).strip()
                    section_statute = section_num + " " + statute
                    if section_statute in self.statutes_df['section_statute'].values:
                        index = self.statutes_df[self.statutes_df['section_statute'] == section_statute].index
                        offence = self.statutes_df.iloc[index].values
                        self.__offences.append([offence[0][1], section_statute])
                except:
                    pass
        except:
            pass
         # If the judgment header does not contain the section and statute, identify it through the text
        if len(self.__offences) == 0:
            print('No offences found in header, checking document text..')
            offence_b = []
            sections_found = []
            statutes_found = []
            self.__search_results2 = self.document.find_all('p', {'class': 'Judg-1'})
            for item in self.__search_results2:
                section_list = []
                statute_list = []
                try:
                    sections = re.findall('( [Ss](ection|)(s|) \d+)', item.text.replace('\xa0',' '))
                    if sections != []:
                        for s in sections:
                            section_list.append(re.findall(r'\d+',s[0]))
                            for ss in section_list:
                                sections_found.append(ss[0])
                    statutes = re.findall(r'((([A-Z][a-z]*)|(of| )*)*(Act|Code))', item.text.replace('\xa0',' '))
                    if statutes != []:
                        for s in statutes:
                            statute_list.append(s[0].strip())
                            for ss in list(statute_list):
                                statutes_found.append(ss)
                except:
                    pass
            try:
                sections = set(sections_found)
                statutes = set(statutes_found)
                combinations = list(itertools.product(list(sections),list(statutes)))
                possible_offences = []
                for offence in combinations:
                    possible_offences.append(' '.join(offence))
                for value in possible_offences:
                    if value in self.statutes_df['section_statute'].values:
                        index = self.statutes_df[self.statutes_df['section_statute'] == section].index
                        offence = self.statutes_df.iloc[index].values
                        offence_b.append([offence[0][1], value])
                        [self.__offences.append(x) for x in offence_b if x not in self.__offences];
                    else:
                        offence_b.append(['Unsure', value])
                        [self.__offences.append(x) for x in offence_b if x not in self.__offences];
            except:
                pass
        self.__title = []
        self.__temp_title = []
        self.__statute = []
        self.__title_statute = {}
        for item in self.__offences:
            self.__temp_title.append(item[0])
            self.__statute.append(item[1])
        self.__temp_title = set(self.__temp_title)
        for title in self.__temp_title:
            self.__title.append(str(title))
        self.__title = ",".join(self.__title)
        self.__statute = ",".join(self.__statute)
        self.__title_statute = {'offences': self.__title, 'statutes': self.__statute}
        return self.__title_statute
     
    def __get_citations(self):
        """
        Searches the document text for case citations which are in the format of `____ v ____`.
        """
        self.__judgment_text = self.__search_results.text.replace('\xa0','')
        self.__case_search = re.findall('((([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))* v (([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))*(?=|))', self.__judgment_text)
        self.__cases = []
        for item in self.__case_search:
            case = []
            case.append(re.search('((([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))* v (([A-Z][a-z]*)|(s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))*(?=|))', str(item)).group(0).strip().replace("In ",""))
            [self.__cases.append(x) for x in case if x not in self.__cases];
        self.__cases.remove(self.__temp_case_name)
        self.__cases = ",".join(self.__cases)
        self.__citations = {'citations': self.__cases}
        return self.__citations
            
    def __get_miscellaneous(self):
        """
        Searches the document text to identify if mitigating factors were discussed, and if aggravating factors were discussed
        """
        if re.search(r'[mM]itigation|[mM]itigating',self.__judgment_text):
            self.__mitigation_discussed = 1
        else:
            self.__mitigation_discussed = 0
            
        if re.search(r'[aA]ggravating|[aA]ggravated',self.__judgment_text):
            self.__aggravated_discussed = 1
        else:
            self.__aggravated_discussed = 0   
        self.__miscellaneous = {'mitigation_discussed': self.__mitigation_discussed, 'aggravated_discussed': self.__aggravated_discussed}
        return self.__miscellaneous
    
    def __get_url(self):
        """
        Adds the url of the case to the dataframe
        
        """
        
        
    def __process_judgments(self, court):
        """
        Loads each new html judgment and performs the NLP steps to extract the key information.
        """
        self.dictionaries_list = []
        self.__start = 0
        if court == 'supreme':
            self.__start = self.__supremecourt_rows - self.__new_supremecourt_rows
            self.__end = self.__supremecourt_rows
        elif court == 'subordinate':
            self.__start = self.__subordinatecourt_rows - self.__new_subordinatecourt_rows
            self.__end = self.__subordinatecourt_rows
        else:
            raise CourtNameError("There is only the Subordinate (State) or Supreme Court!")
        # Load the dataset
        self.dataset = pd.read_csv(f'../data/{court}court_compiled.csv')
        
        if self.__start < self.__end:
            for index in range(self.__start, self.__end):
                # Print current progress
                self.__case_link = self.dataset.loc[index]['link']
                print(f'Current progress: {index+1}/{self.__end}.')
                load_judgment = codecs.open(f'../judgments/{court}_court/{court}court_{index}.html', 'r', 'utf-8')
                print('Judgment loaded')
                self.document = BeautifulSoup(load_judgment.read())
                print('BeautifulSoup initialized')
                self.__search_results = self.document.find('div', {'class': 'contentsOfFile'})
                print('Judgment text identified')
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
                self.__court_column = {'court': court}
                print('tag set')
                self.__add_link = {'link': self.__case_link}
                print('case link set')
                self.__dictionaries_merged = self.__case_name.copy()
#                 print('Case name added to dictionary')
                self.__dictionaries_merged.update(self.__court)
#                 print('Court added to dictionary')
                self.__dictionaries_merged.update(self.__decision_date)
#                 print('Decision date added to dictionary')
                self.__dictionaries_merged.update(self.__title_statute)
#                 print('Statutes added to dictionary')
                self.__dictionaries_merged.update(self.__citations)
#                 print('Citations added to dictionary')
                self.__dictionaries_merged.update(self.__miscellaneous)
#                 print('Miscellaneous added to dictionary')
                self.__dictionaries_merged.update(self.__court_column) 
                self.__dictionaries_merged.update(self.__add_link)
#                 print('tag added to dictionary')
                self.dictionaries_list.append(self.__dictionaries_merged)
#                 print('Judgment added to complete list')
                # Clear cell output
                clear_output(wait=True)
#                 print('Output cleared')


            self.database = pd.DataFrame(self.dictionaries_list)
            # Print current progress
            print(f'Current progress: DataFrame created.')
            self.database_df = self.database_df.merge(self.database, how='outer')
            self.database_df.reset_index(drop=True)
        else:
            self.database = pd.DataFrame()
            print('No new entries')
            

    def __export_database(self):
        """
        Exports dataframes to the respective .csv files
        """
        self.database.to_csv(path_or_buf=f'../data/database_temp.csv', index=False)
        self.database_df.to_csv(path_or_buf=f'../data/database.csv', index=False)

    def create_database(self,court):
        """
        Call command to pull urls and export to csv database
        """
        self.__get_num_rows()
        self.__process_judgments(court)
        self.__export_database()
        self.file = open('../logs/database_log.txt', 'a', encoding='utf_8')
        self.file.write(f'database last updated on: {datetime.today()}; \n')
        # Print current progress
        print(f'Current progress: Completed judgment processing and export.')
        
        
class CourtNameError(Exception):
    pass
