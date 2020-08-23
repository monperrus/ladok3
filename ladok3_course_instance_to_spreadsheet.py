#!/usr/bin/python3
#
# Input:
#    ./ladok3_course_instance_to_spreadsheet.py course_code course_instance
# or
#    ./ladok3_course_instance_to_spreadsheet.py canvas_course_id
#
# Examples:
#  II2202 P1 in 2019 is course instance 50287
# ./ladok3_course_instance_to_spreadsheet.py II2202 50287
#
# II2202 P1 and P1P2 in 2020
# ./ladok3_course_instance_to_spreadsheet.py II2202 51127
# ./ladok3_course_instance_to_spreadsheet.py II2202 51491
#
# II2202 P1 is Canvas course_id 20979
#    ./ladok3_course_instance_to_spreadsheet.py 20979
#
# will produce a file: users_programs-12162.xlsx
# This file will contain the columns:
# 	canvas_user_id	user	ladok_id				program_code	program_name						track_code	admission
# 0	xxxx		xxx,yyy	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	INFKOMTE	Information and Communication Technology		INFKOMTE	KONV-0274B
# 1	xxxx		xxx,yyy	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	TEBSM		Master's Programme, Embedded Systems, 120 credits	TEBSM		E0914
# 2	xxxx		xxx,yyy	xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx	TCOMM		Track, Wireless networking				TRN		TRN2020
#...
#
# It requires a config.json file with (1) the Canvas url and access token and (2) the user's username and password (for access to Ladok)
#
# If run with the flag --testing or -t it calls a lot of the routines to test of the functionality of the various calls to get information from Ladok.
#
# If run with the flag -p or --personnumbers - it includes the personnumber of each student.
#
# Add the "-T" flag to run in the Ladok test environment.
#
## The code in ladok3.py extends the ladok3.py code from Alexander Baltatzis <alba@kth.se> - https://gits-15.sys.kth.se/kthskript/ladok3​ from 2020-07-20.
#
# last modified: 2020-07-23
#

import ladok3,  pprint
import requests, time
import json
import optparse
import sys
import pandas as pd
pp = pprint.PrettyPrinter(indent=4)

global canvas_baseUrl	# the base URL used for access to Canvas
global canvas_header	# the header for all HTML requests
global canvas_payload	# place to store additionally payload when needed for options to HTML requests


def initialize(options):
    global canvas_baseUrl, canvas_header, canvas_payload

    if options.config_filename:
        config_file=options.config_filename
    else:
        config_file='config.json'
    try:
        with open(config_file) as json_data_file:
            configuration = json.load(json_data_file)

            # set up Canvas access
            canvas_access_token=configuration["canvas"]["access_token"]
            if options.containers:
                canvas_baseUrl="http://"+configuration["canvas"]["host"]+"/api/v1"
                print("using HTTP for the container environment")
            else:
                canvas_baseUrl="https://"+configuration["canvas"]["host"]+"/api/v1"

            canvas_header = {'Authorization' : 'Bearer ' + canvas_access_token}
            canvas_payload = {}

            # set up Ladok access
            username=configuration["ladok"]["username"]
            password=configuration["ladok"].get("password", [])
    except:
        print("Unable to open configuration file named {}".format(config_file))
        print("Please create a suitable configuration file, the default name is config.json")
        sys.exit()

    if not password:
        password=getpass.getpass(prompt='Password (for Ladok access): ')
    ls=ladok3.LadokSession(username, password, options.testenvironment)
    return ls


#//////////////////////////////////////////////////////////////////////
# Canvas related routines
#//////////////////////////////////////////////////////////////////////
def users_in_course(course_id):
    users_found_thus_far=[]
    # Use the Canvas API to get the list of users enrolled in this course
    #GET /api/v1/courses/:course_id/enrollments

    url = "{0}/courses/{1}/enrollments".format(canvas_baseUrl,course_id)
    if Verbose_Flag:
        print("url: {}".format(url))

    extra_parameters={'per_page': '100',
                      'type': ['StudentEnrollment']
    }
    r = requests.get(url, params=extra_parameters, headers = canvas_header)
    if Verbose_Flag:
        print("result of getting enrollments: {}".format(r.text))

    if r.status_code == requests.codes.ok:
        page_response=r.json()

        for p_response in page_response:  
            users_found_thus_far.append(p_response)

        # the following is needed when the reponse has been paginated
        while r.links.get('next', False):
            r = requests.get(r.links['next']['url'], headers=canvas_header)
            page_response = r.json()  
            for p_response in page_response:  
                users_found_thus_far.append(p_response)

    return users_found_thus_far

def canvas_user_from_integration_id(integration_id):
    # Use the Canvas API to get the user's informatio
    #GET /api/v1/users/sis_integration_id:xxxxxxx

    url = "{0}/users/sis_integration_id:{1}".format(canvas_baseUrl,integration_id)
    if Verbose_Flag:
        print("url: {}".format(url))

    extra_parameters={'per_page': '100',
    }
    r = requests.get(url, params=extra_parameters, headers = canvas_header)
    if Verbose_Flag:
        print("result of getting user: {}".format(r.text))

    if r.status_code == requests.codes.ok:
        return r.json()

    return None

def teachers_in_course(course_id):
    users_found_thus_far=[]
    # Use the Canvas API to get the list of users enrolled in this course
    #GET /api/v1/courses/:course_id/enrollments

    url = "{0}/courses/{1}/enrollments".format(canvas_baseUrl,course_id)
    if Verbose_Flag:
        print("url: {}".format(url))

    extra_parameters={'per_page': '100',
                      'type': ['TeacherEnrollment']
    }
    r = requests.get(url, params=extra_parameters, headers = canvas_header)
    if Verbose_Flag:
        print("result of getting enrollments: {}".format(r.text))

    if r.status_code == requests.codes.ok:
        page_response=r.json()

        for p_response in page_response:  
            users_found_thus_far.append(p_response)

        # the following is needed when the reponse has been paginated
        while r.links.get('next', False):
            r = requests.get(r.links['next']['url'], headers=canvas_header)
            page_response = r.json()  
            for p_response in page_response:  
                users_found_thus_far.append(p_response)

    return users_found_thus_far

def course_info(course_id):
    # Use the Canvas API to get information for the course
    #GET /api/v1/courses/:course_id

    url = "{0}/courses/{1}".format(canvas_baseUrl,course_id)
    if Verbose_Flag:
        print("url: {}".format(url))

    r = requests.get(url, headers = canvas_header)
    if Verbose_Flag:
        print("result of getting course: {}".format(r.text))

    if r.status_code == requests.codes.ok:
        page_response=r.json()
        return page_response
    return None

def list_dashboard_cards():
    cards_found_thus_far=[]
    # Use the Canvas API to get the list of dashboard cards
    #GET /api/v1/dashboard/dashboard_cards

    url = "{0}/dashboard/dashboard_cards".format(canvas_baseUrl)
    if Verbose_Flag:
        print("url: {}".format(url))

    r = requests.get(url, headers = canvas_header)
    if Verbose_Flag:
        print("result of getting dashboard cards: {}".format(r.text))

    if r.status_code == requests.codes.ok:
        page_response=r.json()

        for p_response in page_response:  
            cards_found_thus_far.append(p_response)

            # the following is needed when the reponse has been paginated
            # i.e., when the response is split into pieces - each returning only some of the list of files
            # see "Handling Pagination" - Discussion created by tyler.clair@usu.edu on Apr 27, 2015, https://community.canvaslms.com/thread/1500
        while r.links.get('next', False):
            r = requests.get(r.links['next']['url'], headers=header)  
            if Verbose_Flag:
                print("result of getting files for a paginated response: {}".format(r.text))
            page_response = r.json()  
            for p_response in page_response:  
                cards_found_thus_far.append(p_response)

    return cards_found_thus_far

#//////////////////////////////////////////////////////////////////////
# Ladok related routines
#//////////////////////////////////////////////////////////////////////
def english_name(names):
    for i in names:
        if i['Sprakkod'] == 'en':
            return i['Text']
        
def swedish_name(names):
    for i in names:
        if i['Sprakkod'] == 'sv':
            return i['Text']

def specialization_info(ls, student_uid):
    s1=ls.studystructure_student_JSON(student_uid)
    ss1=s1['Studiestrukturer']

    # a student who is not in a program will have s1 == {'Studiestrukturer': [], 'link': []}
    if not ss1:
        return ["Self-contained courses - no program"]

    program_code=s1['Studiestrukturer'][0]['Utbildningsinformation']['Utbildningskod']
    print("program_code={}".format(program_code))
    if len(s1['Studiestrukturer'][0]['Barn']) > 0:
        sss1=s1['Studiestrukturer'][0]['Barn'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Benamning']['en']
        sss2=s1['Studiestrukturer'][0]['Barn'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Utbildningskod']
        sss3=s1['Studiestrukturer'][0]['Barn'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Utbildningstillfalleskod']
        sss4=s1['Studiestrukturer'][0]['Barn'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Utbildningstillfallestyp']['Kod']
        return [program_code, sss1, sss2, sss3, sss4]
    else:
        check_for_english_program_name=s1['Studiestrukturer'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Benamning'].get('en', False)
        if check_for_english_program_name:
            sss1=s1['Studiestrukturer'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Benamning']['en']
        else:
            sss1=s1['Studiestrukturer'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Benamning']['sv']
            print("*** No English program name for {}".format(sss1))

        sss2=s1['Studiestrukturer'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Utbildningskod']
        sss3=s1['Studiestrukturer'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Utbildningstillfalleskod']
        sss4=s1['Studiestrukturer'][0]['Tillfallesdeltagande']['Utbildningsinformation']['Utbildningstillfallestyp']['Kod']
        return [program_code, sss1, sss2, sss3, sss4]

#//////////////////////////////////////////////////////////////////////
# utility routines
#//////////////////////////////////////////////////////////////////////
# set up the output write
def write_xlsx(file_name, df, sheet_name):
    writer = pd.ExcelWriter(file_name+'.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name=sheet_name)
    # Close the Pandas Excel writer and output the Excel file.
    writer.save()

def course_id_from_assetString(card):
    global Verbose_Flag

    course_id=card['assetString']
    if len(course_id) > 7:
        if course_id.startswith('course_'):
            course_id=course_id.replace('course_', "", 1)
            if Verbose_Flag:
                print("course_id_from_assetString:: course_id={}".format(course_id))
            return course_id
    else:
        print("Error missing assetString for card {}".format(card))
        return None

# check if the course_id is all digits, matches course code, or matches a short_name
def process_course_id_from_commandLine(course_id):
    if not course_id.isdigit():
        cards=list_dashboard_cards()
        for c in cards:
            # look to see if the string is a course_code
            if course_id == c['courseCode']:
                course_id=course_id_from_assetString(c)
                break
            # check for matched against shortName
            if course_id == c['shortName']:
                course_id=course_id_from_assetString(c)
                break
            # look for the string at start of the shortName
            if c['shortName'].startswith(course_id) > 0:
                course_id=course_id_from_assetString(c)
                print("picked the course {} based on the starting match".format(c['shortName']))
                break
            # look for the substring in the shortName
            if c['shortName'].find(course_id) > 0:
                course_id=course_id_from_assetString(c)
                print("picked the course {} based on partial match".format(c['shortName']))
                break

            # check for matched against originalName
            if course_id == c['originalName']:
                course_id=course_id_from_assetString(c)
                break
            # look for the string at start of the shortName
            if c['originalName'].startswith(course_id) > 0:
                course_id=course_id_from_assetString(c)
                print("picked the course {} based on the starting match".format(c['shortName']))
                break
            # look for the substring in the shortName
            if c['originalName'].find(course_id) > 0:
                course_id=course_id_from_assetString(c)
                print("picked the course {} based on partial match".format(c['shortName']))
                break

        print("processing course: {0} with course_id={1}".format(c['originalName'], course_id))
    return course_id


def main():
    global Verbose_Flag

    parser = optparse.OptionParser()

    parser.add_option('-v', '--verbose',
                      dest="verbose",
                      default=False,
                      action="store_true",
                      help="Print lots of output to stdout"
    )

    parser.add_option("--config", dest="config_filename",
                      help="read configuration from FILE", metavar="FILE")

    parser.add_option('-C', '--containers',
                      dest="containers",
                      default=False,
                      action="store_true",
                      help="for the container enviroment in the virtual machine"
    )

    parser.add_option('-t', '--testing',
                      dest="testing",
                      default=False,
                      action="store_true",
                      help="execute test code"
    )

    parser.add_option('-p', '--personnumbers',
                      dest="pnr",
                      default=False,
                      action="store_true",
                      help="include person numbers"
    )

    parser.add_option('-T', '--testenvironment',
                      dest="testenvironment",
                      default=False,
                      action="store_true",
                      help="execute test code"
    )

    options, remainder = parser.parse_args()

    Verbose_Flag=options.verbose
    if Verbose_Flag:
        print("ARGV      : {}".format(sys.argv[1:]))
        print("VERBOSE   : {}".format(options.verbose))
        print("REMAINING : {}".format(remainder))
        print("Configuration file : {}".format(options.config_filename))

    ladok_session=initialize(options)

    if (len(remainder) == 2):
        course_code=remainder[0]
        instance_code=remainder[1]
    elif (len(remainder) == 1):
        course_id=process_course_id_from_commandLine(remainder[0])
        if not course_id:
            print("Unable to recognize a course_id, course code, or short name for a course in {}".format(remainder[0]))
            return

        # get the "sis_course_id"
        course_information=course_info(course_id)
        course_code=course_information.get('sis_course_id', None)
        if not course_code:
            print("Unable to find course_code information for Canva course={}".format(course_id))
        course_code=course_code[0:6]

        course_integration_id=course_information.get('integration_id', None)
        if not course_integration_id:
            print("Unable to find course_integration information for Canva course={}".format(course_id))
        instance_info=ladok_session.instance_info_uid(course_integration_id)
        if instance_info:
            instance_code=instance_info['TillfallesKod']
            if Verbose_Flag:
                print("instance_code={}".format(instance_code))
        else:
            print("Insuffient arguments - must provide at least a course_code")
            return
    else:
        print("Insuffient arguments - must provide course_code course_instance_id (i.e. the KOPPS Tillfällskod)\n")
        sys.exit()

    utbildningstyp=ladok_session.utbildningstyp_JSON()
    types_of_education=dict()
    for i in utbildningstyp['Utbildningstyp']:
        types_of_education[i['Kod']]={
            'en': i['Benamning']['en'],
            'sv': i['Benamning']['sv'],
        }

    user_and_program_list=[]
    ii=ladok_session.instance_info(course_code, instance_code, 'en')
    if not ii.get('Uid', False):
        print("It seems the instance code is not a Ladok instance ('tillfälleskod'), ii:")
        pp.pprint(ii)
        return

    pl=ladok_session.participants_JSON(ii['Uid'])
    for s in pl['Resultat']:
        d=dict()

        ladok_id=s['Student']['Uid']
        si=specialization_info(ladok_session, ladok_id)
        canvas_user_info=canvas_user_from_integration_id(ladok_id)
        if canvas_user_info:
            d['canvas_user_id']=canvas_user_info['id']
            d['user']=canvas_user_info['sortable_name']
        else:
            d['canvas_user_id']="not in Canvas"
            d['user']=s['Student']['Efternamn']+','+s['Student']['Fornamn']
            
        d['ladok_id']=ladok_id
        if options.pnr:
            d['pnr']=s['Student']['Personnummer']

        d['program_code']=si[0]
        if len(si) > 1:
            d['program_name']=si[1]
            d['track_code']=si[2]
            d['Session_code']=si[3]               # utbildningstillfälleskod
            # the type of education is associated with an application code (anmälningskod)
            d['type_ of_education']=types_of_education[si[4]]['en']
        user_and_program_list.append(d)
        
    user_and_program_df=pd.json_normalize(user_and_program_list)
    output_file="users_programs-instance-{}".format(instance_code)
    write_xlsx(output_file, user_and_program_df, 'users_programs')

    # to logout and close the session
    status=ladok_session.logout()


if __name__ == "__main__": main()

