
import time
import requests
import bs4 as bs
import urllib.request
import re
import json
import os
import concurrent.futures
from urllib.parse import urlencode
#from scrapeops_python_requests.scrapeops_requests import ScrapeOpsRequests
import logging
from dotenv import load_dotenv, find_dotenv
from app.cohere.CohereClient import CohereClient

# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

dotenv_path = find_dotenv('.env.dev', usecwd=True)

if dotenv_path:
    load_dotenv(dotenv_path)

COHERE_API_KEY = os.getenv("CO_API_KEY")
co = CohereClient(COHERE_API_KEY)

class ScrapingClient:
    
    def __init__(self, 
                 scrapeops_api_key=None, 
                 scrapeops_proxy_enabled=True,
                 scrapeops_monitoring_enabled=True,
                 scrapeops_proxy_settings={}, 
                 spider_name=None,
                 job_name=None,
                 num_concurrent_threads=1, 
                 num_retries=1,
                 http_allow_list=[200, 404],
                ):
        self.scrapeops_api_key = scrapeops_api_key
        self.scrapeops_proxy_settings = scrapeops_proxy_settings
        self.scrapeops_proxy_enabled = scrapeops_proxy_enabled
        self.scrapeops_monitoring_enabled = scrapeops_monitoring_enabled
        self.num_concurrent_threads = num_concurrent_threads
        self.num_retries = num_retries
        self.http_allow_list = http_allow_list
        self.spider_name = spider_name
        self.job_name = job_name
        self.sops_request_wrapper = None
        #self.start_scrapeops_monitor()
        
    # def start_scrapeops_monitor(self):
    #     """
    #         Starts the ScrapeOps monitor, which ships logs to dashboard.
    #     """
    #     if self.scrapeops_monitoring_enabled and self.scrapeops_api_key is not None:
    #         try:
    #             self.scrapeops_logger =  ScrapeOpsRequests(
    #                             scrapeops_api_key=self.scrapeops_api_key, 
    #                             spider_name=self.spider_name,
    #                             job_name=self.job_name,
    #                           )
    #             self.sops_request_wrapper = self.scrapeops_logger.RequestsWrapper()
    #         except Exception as e:
    #             print('monitioring error', e)
    #     else:
    #         self.sops_request_wrapper = requests
        
    def scrapeops_proxy_url(self, url, scrapeops_proxy_settings=None):
        """
            Converts URL into ScrapeOps Proxy API URL
        """
        payload = {'api_key': self.scrapeops_api_key, 'url': url}
        
        ## Global Proxy Settings
        if self.scrapeops_proxy_settings is not None and type(self.scrapeops_proxy_settings) is dict:
            for key, value in self.scrapeops_proxy_settings.items():
                payload[key] = value
                
        ## Per Request Proxy Settings
        if scrapeops_proxy_settings is not None and type(scrapeops_proxy_settings) is dict:
            for key, value in self.scrapeops_proxy_settings.items():
                payload[key] = value
                
        proxy_url = 'https://proxy.scrapeops.io/v1/?' + urlencode(payload)
        return proxy_url
    
    def send_request(self, url, method='GET', scrapeops_proxy_settings=None, **kwargs):
        """
            Sends HTTP request and retries failed responses.
        """
        final_url = url
        linkedin_flag = False
        indeed_flag = False
        job_data = {}

        # Check if final_url contains 'linkedin'
        if re.search(r'linkedin', final_url, re.IGNORECASE):
            linkedin_flag = True
        # Check if final_url contains 'indeed'
        if re.search(r'indeed', final_url, re.IGNORECASE):
            indeed_flag = True

        if(linkedin_flag):
            try:
                source = urllib.request.urlopen(final_url)
                soup = bs.BeautifulSoup(source,'lxml')
                div = soup.find("div", class_ = "show-more-less-html__markup show-more-less-html__markup--clamp-after-5 relative overflow-hidden" )
                if div:
                    # summarize with cohere
                    # tempurature zero for the time being.
                    # keeping it at zero allows us to better experiment and tweak things, knowing the LLM is a control.
                    response = co.summarize( 
                        text=div.get_text(),
                        length='short',
                        format='bullets',
                        model='command',
                        additional_command='extract the most important qualifications.',
                        extractiveness='high',
                        temperature=0.0,
                    ) 
                    # first element is always ""
                    clean_response = response.summary.split('- ')[1:]

                    company = soup.find("a", class_="topcard__org-name-link topcard__flavor--black-link").get_text()
                    pattern = r"(?<=\n)(.*?)(?=\n)"
                    clean_company = re.findall(pattern, company)[0]
                    job_title = soup.find("h1", class_="top-card-layout__title font-sans text-lg papabear:text-xl font-bold leading-open text-color-text mb-0 topcard__title").get_text()
                    return {"contents" : clean_response, 'company': clean_company, 'job_title': job_title}
                else:
                    return {"error" : "div not found"}
            except Exception as e:
                print('Request error:', e)
        if(indeed_flag):
            pattern = r'jk=([0-9a-fA-F]+)'
            match = re.search(pattern, final_url)
            job_id = ''
            if match:
                job_id = match.group(1)
                #print(job_id)
            try:
                indeed_job_url = 'https://www.indeed.com/m/basecamp/viewjob?viewtype=embedded&jk=' + job_id
                if self.scrapeops_proxy_enabled and self.scrapeops_api_key is not None:
                    final_url = self.scrapeops_proxy_url(indeed_job_url, scrapeops_proxy_settings)
                for _ in range(self.num_retries):
                    try:
                        response = requests.get(final_url, **kwargs)
                        if response.status_code in self.http_allow_list:
                            #print('RESPONSE: ', response.text)
                            script_tag  = re.findall(r"_initialData=(\{.+?\});", response.text)
                            if script_tag is not None:
                                json_blob = json.loads(script_tag[0])
                                job = json_blob["jobInfoWrapperModel"]["jobInfoModel"]
                                job_data[job_id] = {
                                'company': job['jobInfoHeaderModel']['companyName'] if job['jobInfoHeaderModel']['companyName'] is not None else '',
                                'jobkey': job_id,
                                'jobTitle': job['jobInfoHeaderModel']['jobTitle'] if job['jobInfoHeaderModel']['jobTitle'] is not None else '',
                                'jobDescription': job['sanitizedJobDescription'] if job['sanitizedJobDescription'] is not None else '',
                            }
                            def is_qualification_header(tag):
                                return (tag.name == 'h2' or tag.name == 'p') and 'Qualifications' in tag.text
                            
                            #print('JOB DESC: ', job_data[job_id]['jobDescription'])
                            soup = bs.BeautifulSoup(job_data[job_id]['jobDescription'], 'html.parser')
                            qualifications_headers = soup.find(is_qualification_header)
            
                            qualifications = []
                            if qualifications_headers:
                                # Find the next <ul> tag after the <h2> tag
                                ul_tag = qualifications_headers.find_next('ul')
                                if ul_tag:
                                    for li_tag in ul_tag.find_all('li'):
                                        qualifications.append(li_tag.get_text())

                            for qualification in qualifications:
                                print('qualifcation: ', qualification)
                            # summarize with cohere
                            # tempurature zero for the time being.
                            # keeping it at zero allows us to better experiment and tweak things, knowing the LLM is a control.
                            qualificationsResponse = co.summarize( 
                                text=', '.join(qualifications),
                                length='short',
                                format='bullets',
                                model='command',
                                additional_command='extract the most important qualifications.',
                                extractiveness='high',
                                temperature=0.0,
                            ) 
                            # first element is always ""
                            clean_response = qualificationsResponse.summary.split('- ')[1:]
                            return {"contents" : clean_response, 'company': job_data[job_id]['company'], 'job_title': job_data[job_id]['jobTitle']}
                    except Exception as e:
                        print('Request error:', e)
                return None
            except Exception as e:
                print('Overall error', e)

      
    def concurrent_requests(self, function, input_list):
        """
            Enables requests to be sent in parallel
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_retries) as executor:
            executor.map(function, input_list)