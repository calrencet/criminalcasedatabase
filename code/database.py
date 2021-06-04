from __future__ import division, unicode_literals 
import codecs
from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import numpy as np
from time import sleep
from random import randint
from datetime import datetime
from IPython.display import clear_output

class Database:

    def __init__(self):
        """
        Initializes the class and loads the datasets.
        """
        self.courts = ['subordinate', 'supreme']
        self.supremecourt_df = pd.read_csv('../data/supremecourt_compiled.csv')
        self.subordinatecourt_df = pd.read_csv('../data/subordinatecourt_compiled.csv')
        self.database_df = pd.read_csv('../data/database.csv')
        self.statutes_df = pd.read_csv('../data/statutes.csv')
        
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
        print(self.__case_name)
        return self.__case_name
    
    def __get_court(self):
        """
        Takes out the court name from the judgment
        """
        self.__temp_results1 = self.__search_results.find('table', {'id': 'info-table'})
        self.__court = {re.search('Tribunal/Court : (\w* )*(?=Coram)', self.__temp_results1.text).group(0).strip()
        print(self.__court)
        return self.__court
                        
    def __get_date(self):
        """
        Takes out the court name from the judgment
        """
        self.__temp_results1 = self.__search_results.find('table', {'id': 'info-table'})
        self.__date = {re.search('Decision Date : (\w* )*(?=Tribunal)', self.__temp_results1.text).group(0).strip()
        print(self.__date)
        return self.__date
        
    def __get_statute(self):
        """
        Identifies criminal offences and statutes mentioned in the judgment based on its header as a first choice, and text as a second choice.
        """
        self.__offences = []
        # First try to identify the crimes based on the header of the judgment.
        self.__temp_results1 = self.__search_results.find('p', {'class': 'txt-body'})
        self.__temp_results2 = self.__temp_results1.find_all('span')
        for item in self.__temp_results2:
            print(item.text)
            try:
                section = re.search('[Ss](ection|s|) \d*', item.text).group(0).strip()
                section = re.sub('[Ss](ection|s|) ', "", section)
                statute = re.search('([A-Za-z]* )*([Aa]ct|[Cc]ode)', item.text).group(0).strip()
                section_statute = section + " " + statute
                if section_statute in statutes_df['section_statute'].values:
                    index = statutes_df[statutes_df['section_statute'] == section_statute].index
                    offence = statutes_df.iloc[index].values
                    self.__offences.append([offence[0][1], section_statute])
            except:
                pass
         # If the judgment header does not contain the section and statute, identify it through the text
        if len(self.__offences) == 0:
            # Clear cell output
            clear_output(wait=True)
            print('No offences found in header, checking document text..')
            offence_b = []
            self.__search_results2 = self.document.find_all('p', {'class': 'Judg-1'})
            for item in self.__search_results2:
                try:
                    sections = re.findall('[Ss]ection \d*', item.text)
                    print(sections)
                    statutes = [re.findall('(([A-Z][a-z]* )*([Aa]ct|[Cc]ode))', item.text)[0][0]]
                    print(statutes)
                    statutes.append(re.findall('(([A-Z][a-z]* )*([Aa]ct|[Cc]ode))', item.text)[1][0])
                    print(statutes)
                    try:
                        sections_statutes = set(zip(sections, statutes))
                        print(sections_statutes)
                        for value in list(sections_statutes):
                            section = re.sub('[Ss]ection ', "", value[0]) + " " + value[1]
                            print(section)
                            if section in statutes_crimes['section_statute'].values:
                                index = statutes_crimes[statutes_crimes['section_statute'] == section].index
                                print(index)
                                offence = statutes_crimes.iloc[index].values
                                print(offence)
                                offence_b.append([offence[0][1], section])
                                [self.__offences.append(x) for x in offence_b if x not in self.__offences];
                    except:
                        pass
                except:
                    pass
        self.__title = []
        self.__statute = []
        self.__title_statute = {}
        for item in self.__offences:
            self.__title.append(item[0])
            self.__statute.append(item[1])
        self.__title_statute = {'offences': self.__title, 'statutes': self__statute}
        return self.__title_statute
     
    def __get_citations(self):
        """
        Searches the document text for case citations which are in the format of `____ v ____`.
        """
        self.__judgment_text = self.__search_results.text.replace('\xa0','')
        self.__case_search = re.findall('(((([A-Z][a-z]*)(( |bte|bin|and|another| anr|binti|de|the|for)*))*) v ((([A-Z][a-z]*)(( |bte|bin|and|another| anr|binti|de|the|for)*))*)(?=|))', self.__judgment_text)
        self.__cases = []
        for item in self.__case_search:
            case = []
            case.append(re.search('(((([A-Z][a-z]*)(( |bte|bin|and|another| anr|binti|de|the|for)*))*) v ((([A-Z][a-z]*)(( |bte|bin|and|another| anr|binti|de|the|for)*))*)(?=|))', str(item)).group(0))
            print(case)
            [self.__cases.append(x) for x in case if x not in self.__cases];
        self.__citations = {'citations': self.__cases}
            
    def __get_miscellaneous(self):
        """
        Searches the document text to identify if mitigating factors were discussed, and if aggravating factors were discussed
        """
        self.__mitigation_discussed = []
        if re.search(r'[mM]itigation',self.__judgment_text):
            self.__mitigation_discussed.append(1)
        else:
            self.__mitigation_discussed.append(0)
        self.__aggravated_discussed = []
        if re.search(r'[aA]ggravating',self.__judgment_text):
            self.__aggravated_discussed.append(1)
        else:
            self.__aggravated_discussed.append(0)   
        self.__miscellaneous = {'mitigation_discussed': self.__mitigation_discussed, 'aggravated_discussed': self.__aggravated_discussed}
        return self.__miscellaneous
        
        
    def __process_judgments(self, court):
        """
        Loads each new html judgment and performs the NLP steps to extract the key information.
        """
        self.dictionaries_list = []
        self.__start = 0
        if court = 'supreme':
            self.__start = self.supremecourt_rows - self.__new_supremecourt_rows
            self.__end = self.__new_supremecourt_rows+1
        elif court = 'subordinate':
            self.__start = self.subordinatecourt_rows - self.__new_subordinatecourt_rows
            self.__end = self.__new_subordinatecourt_rows+1
        else:
            raise CourtNameError("There is only the Subordinate (State) or Supreme Court!")
        # Load the dataset
        self.dataset = pd.read_csv(f'../data/{court}court_compiled.csv')
        for index in range(self.__start, self.supremecourt_rows, 1):
            load_judgment = codecs.open((f'../judgments/{court}_court/{court}court_{index}.html', 'r', 'utf-8')
            self.document = BeautifulSoup(load_judgment.read())
            self.__search_results = self.document.find('div', {'class': 'contentsOfFile'})
            self.__get_case_name()        
            self.__get_court()
            self.__get_date()                            
            self.__get_statute()                            
            self.__get_citations()                           
            self.__get_miscellaneous()                           
            self.__dictionaries_merged = {**self.__case_name, **self.__court, **self.__date **self.__title_statute, **self.__citations, **self.__miscellaneous, 'court': court}   
            self.dictionaries_list.append(self.__dictionaries_merged)
            # Clear cell output
            clear_output(wait=True)

            # Print current progress
            print(f'Current progress: {index}/{self.__end}.')
        self.database = pd.DataFrame(self.dictionaries_list)
        # Print current progress
        print(f'Current progress: DataFrame created.')
        self.database_df.merge(self.database, how='outer')
        self.database_df.reset_index(drop=True)

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
