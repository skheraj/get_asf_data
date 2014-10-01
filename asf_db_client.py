#!usr/bin/env python

import mysql.connector, dbm
from datetime import date, datetime

CNX = None

CATEGORY_LIST = ['big-data','build-management','cloud','content','database',
                 'http','httpd-modules','javaee','library','mail','mobile',
                 'network-client','network-server','osgi','retired','testing',
                 'web-framework','xml']

LANGUAGE_LIST = ['C','Ruby','Delphi','C++','Cocoa','Objective-C','SVG','JSP',
                 'SmallTalk','Haskell','JavaScript','Scala','ActionScript','Bash',
                 'SQL','node.js','Tcl','Ocaml','Python','Go','Groovy','C#','Java',
                 'XML','Erlang','D','PHP','Perl']

INSERT_PROJECT = (
    "INSERT INTO `asf_data`.`project`"
    "(`name`,"
    "`date_created`,"
    "`homepage`,"
    "`description`,"
    "`bug_database`,"
    "`mailing_list`,"
    "`repository`,"
    "`category`,"
    "`programming_language`,"
    "`version_control`)"
    "VALUES"
    "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    "ON DUPLICATE KEY UPDATE"
    "`date_created`=%s,"
    "`homepage`=%s,"
    "`description`=%s,"
    "`bug_database`=%s,"
    "`mailing_list`=%s,"
    "`repository`=%s,"
    "`category`=%s,"
    "`programming_language`=%s,"
    "`version_control`=%s"
)

INSERT_COMMIT = (
    "INSERT INTO `asf_data`.`commit`"
    "(`commit_id`,"
    "`username`,"
    "`date`,"
    "`comment`,"
    "`project`)"
    "VALUES"
    "(%s, %s, %s, %s, %s)"
    "ON DUPLICATE KEY UPDATE"
    "`username`=%s,"
    "`date`=%s,"
    "`comment`=%s,"
    "`project`=%s"
)

INSERT_MODIFIED_FILE = (
    "INSERT INTO `asf_data`.`modified_file`"
    "(`name`,"
    "`action`,"
    "`commit_id`)"
    "VALUES"
    "(%s, %s, %s)"
    "ON DUPLICATE KEY UPDATE"
    "`action`=%s"
)

def insert_project(project):
    cur = CNX.cursor(buffered=True)
    
    if project['created']:
        tmp = project['created'].split('-')
        if len(tmp) == 3: 
            date_created = date(int(tmp[0]), int(tmp[1]), int(tmp[2]))
        else:
            date_created = None
    else:
        date_created = None

    name = project['name'] if project['name'] else None
    homepage = project['homepage'] if project['homepage'] else None
    description = project['description'] if project['description'] else None
    bug_database = project['bug-database'] if project['bug-database'] else None
    mailing_list = project['mailing-list'] if project['mailing-list'] else None
    repository = project['repository'] if project['repository'] else None
    version_control = project['version_control'] if project['version_control'] else 'n/a'
    
    category = None
    for c in project['categories']:
        if c in CATEGORY_LIST:
            if not category:
                category = c
            else:
                category = category + "," + c
    
    programming_language = None
    for l in project['programming-languages']:
        if l in LANGUAGE_LIST:
            if not programming_language:
                programming_language = l
            else:
                programming_language = programming_language + "," + l
    
    # Check not NULL column constraints
    if name and repository and version_control:
        cur.execute(INSERT_PROJECT, (name, date_created, homepage, description, bug_database, mailing_list, repository, category, programming_language, version_control,
                                           date_created, homepage, description, bug_database, mailing_list, repository, category, programming_language, version_control))
    
    return True

def insert_commit(commit):
    cur = CNX.cursor(buffered=True)
    
    commit_id = commit['commit_id'] if commit['commit_id'] else None
    username = commit['username'] if commit['username'] else None
    date = datetime.strptime(commit['date'], "%Y-%m-%d %H:%M:%S %z") if commit['date'] else None
    comment = commit['comment'] if commit['comment'] else None
    project = commit['project'] if commit['project'] else None
    
    # Check not NULL column constraints
    if commit_id and username and date and project:
        cur.execute(INSERT_COMMIT, (commit_id, username, date, comment, project,
                                               username, date, comment, project))
    else:
        return False
    
    return True

def insert_modified_file(file):
    cur = CNX.cursor(buffered=True)
    
    name = file['name'] if file['name'] else None
    action = file['action'] if file['action'] else None
    commit_id = file['commit_id'] if file['commit_id'] else None
    
    # Check not NULL column constraints; also check that 'name' is less than 250 characters
    if name and action and commit_id and len(name) < 250:
        cur.execute(INSERT_MODIFIED_FILE, (name, action, commit_id, action))
    else:
        return False
    
    return True

def open_connection():
    global CNX
    print("Opening connection to database.")
    db = dbm.open('db_credentials', 'c')
    
    # check for db credentials
    if not 'user' in db or not 'password' in db or not 'database' in db:
        return False
    
    USER = db['user'].decode("utf-8")
    PASSWORD = db['password'].decode("utf-8")
    DATABASE = db['database'].decode("utf-8")
    
    CNX = mysql.connector.connect(user=USER, password=PASSWORD, database=DATABASE)
    
    return True

def close_connection():
    global CNX
    print("Closing connection to database.")
    CNX.commit()
    CNX.close
    CNX = None