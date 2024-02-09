#!/usr/bin/python3
#Artem Zagvozkin
#Get descriptions of java libraries from 
# GPT 3.5 and 
# websites (jarcasting.com, mavenjar.com, mvnrepository.com, ossindex.sonatype.org)
# with Google.Translator

from googletrans import Translator
from lxml import html
from selenium import webdriver
import numpy
import re
import requests
import time
import json


src_file = "src/all_9.csv"
dst_file = "dst/all_9.csv"
num_of_attempts = 3 #due to a bad connection, request may not pass

# GPT properties
gpt_prompter = True
openai_tokens = (
    "",
    "",
    "",
    ""
)
current_token = 0
requests_per_token = 0
requests_per_token_max = 150
translate_prompt = True
prompt_template = "Describe the java library 'java_lib', specify what it contains"

# Site parser properties
site_parser = True
max_results = 30
request_delay = 0.05


########################################
### services ###########################
def print_to_dst_file(*fields):
    line = ";".join(fields) + "\n"

    with open(dst_file, "a", encoding="utf-8") as file:
        file.write(line)
        file.close()

def browser_http_get(url):    
    retries = 1
    while True:
        try:
            browser.get(url)
            print(f"HTTP.GET: '{url}': ok")
            return browser.page_source
        except:
            if retries >= num_of_attempts:
                return ""
            retries += 1
            print(f"HTTP.GET: '{url}': error")
            browser = webdriver.Chrome()
            browser.set_window_rect(0, 0, 400, 400)


def http_get(url):
    time.sleep(request_delay)

    headers = {
        "User-Agent": "PostmanRuntime/7.35.0",
        "Content-Type": "text/html; charset=utf-8"
    }
    
    retries = 1
    while True:
        try:
            response = requests.get(url, headers=headers)
            print(f"HTTP.GET: '{url}': ok")
            return response.content.decode(response.encoding)
        except:
            if retries >= num_of_attempts:
                return ""
            retries += 1
            print(f"HTTP.GET: '{url}': error")

def get_from_html(html_doc, path):
    try:
        xml = html.fromstring(html_doc)
        result = xml.xpath(path)[0].replace(";", ".")
        return re.sub("[\n\r\t]|[\s]{2,}", " ", result)
    except IndexError:
        return ""

def translate(en_text):
    if len(en_text) <= 0:
        return ""
    
    retries = 1
    while True:
        try:
            translation = translator.translate(en_text, src="en", dest="ru")
            print(f"Translate: '{en_text[:10]}...': ok")
            return translation.text
        except:
            if retries >= num_of_attempts:
                return ""
            retries += 1
            print(f"Translate: '{en_text[:10]}...': error")
### services ###########################
########################################


########################################
### site parser ########################
def ranking_results(lib_name_less, lib_name_full, results):
    lib_name_full_formatted = re.sub("[-.:]", " ", lib_name_full).lower()
    runked_results = []
    links = []

    #100% match
    for result in results:
        (source, name, link) = result

        if lib_name_full == name and link not in links:
            results.remove(result)
            runked_results.append(result)
            links.append(link)

    #formatted strings, 100% match
    for result in results:
        (source, name, link) = result
        name = re.sub("[-.:]", " ", name)
        name = re.sub("[\s]{2,}", " ", name).lower()

        if lib_name_full_formatted == name and link not in links:
            results.remove(result)
            runked_results.append(result)
            links.append(link)

    #partial match
    for result in results:
        (source, name, link) = result

        if lib_name_full in name and link not in links:
            results.remove(result)
            runked_results.append(result)
            links.append(link)

    #formatted strings, partial match
    for result in results:
        (source, name, link) = result
        name = re.sub("[-.:]", " ", name)
        name = re.sub("[\s]{2,}", " ", name).lower()

        if (lib_name_full_formatted in name or name in lib_name_full_formatted) and link not in links:
            results.remove(result)
            runked_results.append(result)
            links.append(link)

    #lib name less, partial match
    for result in results:
        (source, name, link) = result

        if lib_name_less in name and link not in links:
            results.remove(result)
            runked_results.append(result)
            links.append(link)

    return runked_results


def get_links(source, search_string):
    search_string = search_string.replace(".", "%2F")

    full_names = []
    links = []
    match source:
        case "jarcasting":
            search_results = http_get("https://jarcasting.com/search/?q=" + search_string).split("\n")
            
            for search_result in search_results:
                words = search_result.split(" : ")
                if len(words) < 2:
                    continue

                full_names.append(f"{words[0]}.{words[1]}.{words[2].split(' ')[0]}")
                links.append(f"https://jarcasting.com/artifacts/{words[0]}/{words[1]}/")
        
        case "mavenjar":
            mavenjar_html = http_get("https://mavenjar.com/search?q=" + search_string)
            xml_doc = html.fromstring(mavenjar_html)

            # full names
            full_names = xml_doc.xpath('//div[@class="subtitle mb-2"]/a/text()')
            full_names = numpy.reshape(full_names, (-1, 3))
            full_names = [".".join(full_name) for full_name in full_names]

            # links
            links = xml_doc.xpath('//a[@class="text-dark"]/@href')
            links = ["https://mavenjar.com" + link for link in links]
        
        case "mvnrepository":
            mvnrepository_html = browser_http_get("https://mvnrepository.com/search?q=" + search_string)
            xml_doc = html.fromstring(mvnrepository_html)

            # full names
            full_names = xml_doc.xpath('//p[@class="im-subtitle"]/a/text()')
            full_names = numpy.reshape(full_names, (-1, 2))
            full_names = [".".join(full_name) for full_name in full_names]

            # links
            links = xml_doc.xpath('//h2[@class="im-title"]/a/@href')
            links = ["https://mvnrepository.com" + link for link in links if ("/usages" not in link)]
        
        case "sonatype":
            sonatype_html = http_get("https://ossindex.sonatype.org/search?type=maven&q=" + search_string)
            xml_doc = html.fromstring(sonatype_html)

            # full names
            full_names = xml_doc.xpath('//td/a/text()')
            full_names = [full_name.replace('/', ".").strip() for full_name in full_names]

            # links
            links = xml_doc.xpath('//td/a/@href')

    return list(zip([source]*len(links), full_names, links))


def search_java_lib(lib_num, lib_name_full, lib_name_less, sources):
    links = []
    for source in sources:
        links += get_links(source, lib_name_full)
        links += get_links(source, lib_name_less)
    links = ranking_results(lib_name_less, lib_name_full, links)

    for i, (source, full_name, link) in enumerate(links):
        match source:
            case "jarcasting":
                response = http_get(link)
                head = get_from_html(response, '//h1/text()')
                description = get_from_html(response, '//div[@class="a-d description"]/text()')
            case "mavenjar":
                response = http_get(link)
                head = get_from_html(response, '//div[@class="card-body pb-2"]/h2/text()')
                description = get_from_html(response, '//div[@class="card-body pb-2"]/p/text()')
            case "mvnrepository":
                response = browser_http_get(link)
                head = get_from_html(response, '//h2[@class="im-title"]/a/text()')
                description = get_from_html(response, '//div[@class="im-description"]/text()')
            case "sonatype":
                response = http_get(link)
                head = get_from_html(response, '//p[@id="component-description-content"]/text()')
                description = get_from_html(response, '//p[@class="see-more-content"]/text()')
        
        translation = translate(description)

        # print to dst file
        print_to_dst_file(str(lib_num), source, str(i+1), head, full_name, translation, description, link)

        if i+1 >= max_results:
            return
### site parser ########################
########################################


########################################
### gpt prompter #######################
def openai_request(prompt):
    global current_token

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_tokens[current_token]}"
    }

    body = {
            "model":"gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": f"{prompt}"
                }
            ]
    }

    retries = 1
    while True:
        try:
            global requests_per_token, requests_per_token_max

            #send request
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)

            #inc requests_per_token
            requests_per_token += 1
            if requests_per_token >= requests_per_token_max:
                requests_per_token = 0
                current_token += 1
                if current_token >= len(openai_tokens):
                    current_token = 0

            return response.content.decode()
        except requests.ConnectionError:
            if retries >= num_of_attempts:
                return "Error"
            retries += 1
            print(f"Prompt: '{prompt}': error")


def get_from_openai(lib_num, lib_name_full):
    prompt = prompt_template.replace('java_lib', lib_name_full)
    response = openai_request(prompt)
    if response == "Error":
        print(f"Prompt: '{prompt}', token: '{openai_tokens[current_token]}': error")
        print_to_dst_file(str(lib_num), "openai", "", "", "", "Error 1", "Error 1", prompt)
        return
    
    # parse response
    description = ""
    try:
        description = json.loads(response)['choices'][0]['message']['content']
    except:
        print(f"Prompt: '{prompt}', token: '{openai_tokens[current_token]}': error")
        print_to_dst_file(str(lib_num), "openai", "", "", "", "Error 2", "Error 2", prompt)
        return

    # text preparation
    description = re.sub("[;\n\t\r]", " ", description)

    # translate
    description_ru = description
    if translate_prompt:
        description_ru = translate(description)

    print_to_dst_file(str(lib_num), "openai", "", "", "", description_ru, description, prompt)
    print(f"Prompt: '{prompt}', token: '{openai_tokens[current_token]}': ok")
### gpt prompter #######################
########################################


# init services
translator = Translator(service_urls=['translate.google.com'])
if site_parser:
    browser = webdriver.Chrome()
    browser.set_window_rect(0, 0, 100, 100)

# clear dst file
with open(dst_file, "w", encoding='utf-8') as file:
    file.write("")
    file.close()

# read src file
with open(src_file, 'r', encoding='utf-8') as file:
    while True:
        line = file.readline()
        if not line:
            file.close()
            break
        [lib_num, lib_name_full, lib_name_less, lib_description_ru] = line.replace("\n", "").split(";")

        # print original
        print_to_dst_file(str(lib_num), "original", "", lib_name_less, lib_name_full, lib_description_ru, "", "")

        # get description from open ai
        if gpt_prompter:
            get_from_openai(lib_num, lib_name_full)

        # get description from external sources
        if site_parser:
            search_java_lib(lib_num, lib_name_full, lib_name_less, ["jarcasting", "mavenjar", "mvnrepository", "sonatype"])

        # print empty line
        print_to_dst_file("", "", "", "", "", "", "", "")
