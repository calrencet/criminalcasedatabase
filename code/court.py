import requests
from bs4 import BeautifulSoup
import pandas as pd
from time import sleep
from random import randint
from datetime import datetime
from IPython.display import clear_output

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
                        if len(result) == 3:
                            self.results_list.append(result)
                    # Clear cell output
                    clear_output(wait=True)

                    # Print current progress
                    print(f'Current progress: page {self.current_page}/{self.last_page}.')
                    
            # Raise page counter
            self.current_page += 1
        self.court_df = pd.DataFrame(self.results_list)
        self.court_df = self.court_df.sort_values(by='date')
        # Print current progress
        print(f'Current progress: DataFrame created.')

    def __only_crim(self):
        """
        Narrows results to only Criminal cases
        """
        self.court_df = self.court_df[self.court_df['title'].str.contains("Public Prosecutor")]

        # Print current progress
        print(f'Current progress: Narrowed to only Criminal cases.')

    def __compare_csv(self):
        """
        Loads the complete csv database and compares data with the dataframe to identify new entries.
        Returns new entries as `court_df` and all entries as `court_full`.
        """
        self.court_full = pd.read_csv(f'../data/{self.name}court_compiled.csv')
        self.court_df = self.court_df[~self.court_df['link'].isin(self.court_full['link'])]
        self.court_full = self.court_full.merge(self.court_df, how='outer')
        
        # Print current progress
        print(f'Current progress: New entries identified and saved.')

    def __export_csv(self):
        """
        Exports dataframes to the respective .csv files
        """
        self.court_df.to_csv(path_or_buf=f'../data/{self.name}court.csv', index=False,date_format='%dd%Mmm%yy')
        self.court_full.to_csv(path_or_buf=f'../data/{self.name}court_compiled.csv', index=False,date_format='%dd%Mmm%yy')

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
        self.file.write(f'list last updated on: {datetime.today()}')
        # Print current progress
        print(f'Current progress: Completed url pull and export.')        

    def __load_csv(self):
        """
        Loads .csvs using `name` as lists of dictionaries.
        """
        self.court_link_list = [pd.read_csv(f'../data/{self.name}court.csv').link.to_dict()]
        self.court_link_dict = pd.read_csv(f'../data/{self.name}court_compiled.csv').link.to_dict()

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
                    print(f'Current progress: {self.count}/{len(self.court_link_list)}.')
                    self.count += 1
                    
                except:
                    # Skip if error, print an error log with index
                    file = open('../logs/error_log.txt', 'a', encoding='utf_8')
                    file.write(f'{self.file_name}_list error: {key}')

    def archive(self):
        """
        Call command to archive the urls as .html files.
        """
        self.__load_csv()
        self.__set_file_name()
        self.__save_html()
        self.file = open('../logs/archival_log.txt', 'a', encoding='utf_8')
        self.file.write(f'last archived on: {datetime.today()}')
        # Print current progress
        print(f'Current progress: HTMLs archived.')        

class CourtNameError(Exception):
    pass
