#!usr/bin/env python

from jira.client import JIRA
from lxml import etree
from datetime import date, datetime
import re, os, dbm, unicodedata, string
import asf_db_client

JIRA_CONN = None

def get_all_comments(issue):
    issue_key = issue.key
    
    comments = JIRA_CONN.comments(issue)
    
    for c in comments:
        comment = {}
        
        comment['issue_key'] = issue_key
        
        comment['author_username'] = c.author.name if hasattr(c, 'author') else None
        author_fullname = c.author.displayName if hasattr(c, 'author') else None
        if author_fullname:
            match = re.search('(\S*\s\S*)\s*', author_fullname)
            if match:
                comment['author_fullname'] = match.group(1)
            else:
                comment['author_fullname'] = author_fullname
        else:
            comment['author_fullname'] = None
        
        # remove non-ascii characters from body string
        body = c.body if hasattr(c, 'body') else None
        if body:
            comment['body'] = ''.join(list(filter(lambda x: x in string.printable, body)))
        else:
            comment['body'] = None
        
        author_email = None
        if hasattr(c, 'author') and hasattr(c.author, 'emailAddress'):
               author_email = c.author.emailAddress
               author_email = author_email.replace(' at ', '@')
               author_email = author_email.replace(' dot ', '.')
               if len(author_email) > 50:
                   author_email = None
        comment['author_email'] = author_email
        
        date_str = c.created if hasattr(c, 'created') else None
        date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        comment['created'] = date
        
        comment['id'] = int(c.id)
        
        asf_db_client.insert_jira_comment(comment)
    
    return True

def get_all_issues(key, name):
    # last_issue_date.db maps a project name to the date of the last issue update
    db = dbm.open('last_issue_date', 'c')

    date_str = ""
    if name in db:
        date_str = db[name].decode("utf-8")
    else:
        date_str = "1970-01-01T00:00:00.000+0000"

    last_update_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")

    # 'EXEC' is a reserved JQL word. You must surround it in quotation marks to use it in a query.
    if key == 'EXEC':
        issues = JIRA_CONN.search_issues("project='EXEC' AND updated>" + "'" + last_update_date.strftime("%Y/%m/%d %H:%M") + "'", startAt=0, maxResults=100)
        size = len(issues)
        n = 100
        
        while size == 100:
            tmp_issues = JIRA_CONN.search_issues("project='EXEC' AND updated>" + "'" + last_update_date.strftime("%Y/%m/%d %H:%M") + "'", startAt=n, maxResults=100)
            size = len(tmp_issues)
            issues = issues + tmp_issues
            n = n + 100
        
    else:
        issues = JIRA_CONN.search_issues("project=" + key + " AND updated>" + "'" + last_update_date.strftime("%Y/%m/%d %H:%M") + "'", startAt=0, maxResults=100)
        size = len(issues)
        n = 100
        
        while size == 100:
            tmp_issues = JIRA_CONN.search_issues("project=" + key + " AND updated>" + "'" + last_update_date.strftime("%Y/%m/%d %H:%M") + "'", startAt=n, maxResults=100)
            size = len(tmp_issues)
            issues = issues + tmp_issues
            n = n + 100

    for i in issues:
        issue = {}

        # check for date of most recently updated issue
        date_str = i.fields.updated
        date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        if date > last_update_date:
            last_update_date = date

        print(i.key)
        
        issue['assignee_username'] = i.fields.assignee.name if i.fields.assignee else None
        issue['reporter_username'] = i.fields.reporter.name if i.fields.reporter else None
        
        assignee_fullname = i.fields.assignee.displayName if i.fields.assignee else None
        if assignee_fullname:
            match = re.search('(\S*\s\S*)\s*', assignee_fullname)
            if match:
                issue['assignee_fullname'] = match.group(1)
            else:
                issue['assignee_fullname'] = assignee_fullname
        else:
            issue['assignee_fullname'] = None
            
        assignee_email = None
        if hasattr(i, 'fields') and hasattr(i.fields, 'assignee') and hasattr(i.fields.assignee, 'emailAddress'):
               assignee_email = i.fields.assignee.emailAddress
               assignee_email = assignee_email.replace(' at ', '@')
               assignee_email = assignee_email.replace(' dot ', '.')
               if len(assignee_email) > 50:
                   assignee_email = None
        issue['assignee_email'] = assignee_email
        
        reporter_fullname = i.fields.reporter.displayName if i.fields.reporter else None
        if reporter_fullname:
            match = re.search('(\S*\s\S*)\s*', reporter_fullname)
            if match:
                issue['reporter_fullname'] = match.group(1)
            else:
                issue['reporter_fullname'] = reporter_fullname
        else:
            issue['reporter_fullname'] = None
            
        reporter_email = None
        if hasattr(i, 'fields') and hasattr(i.fields, 'reporter') and hasattr(i.fields.reporter, 'emailAddress'):
               reporter_email = i.fields.reporter.emailAddress
               reporter_email = reporter_email.replace(' at ', '@')
               reporter_email = reporter_email.replace(' dot ', '.')
               if len(reporter_email) > 50:
                   reporter_email = None
        issue['reporter_email'] = reporter_email
        
        # remove non-ascii characters from description string
        description = i.fields.description
        if description:
            issue['description'] = ''.join(list(filter(lambda x: x in string.printable, description)))
        else:
            issue['description'] = None
        
        issue['key'] = i.key
        issue['type'] = i.fields.issuetype.name
        issue['project'] = name
        issue['status'] = i.fields.status.name

        date_str = i.fields.created
        date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        issue['created'] = date

        res = asf_db_client.insert_jira_issue(issue)
        
        if res:
            get_all_comments(i)

    db[name] = last_update_date.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    
    return True
    
    
def generate_jira_data():
    global JIRA_CONN
    
    JIRA_CONN = JIRA(server='https://issues.apache.org/jira', basic_auth=('', ''))
    files = os.listdir('doap_files')

    project_names = []
    for f in files:
        if 'rdf' in str(f):
            tree = etree.parse('doap_files/' + f)
            root = tree.getroot()
            bug_db = root.find('bug-database').text
            name = root.find('name').text
            if bug_db and 'issues.apache.org/jira' in bug_db:
                project_key_and_name = (os.path.basename(bug_db), name)
                project_names.append(project_key_and_name)
    
    project_names = [p for p in project_names if p[0] and not p[0].isspace()]
    
    for name in project_names:
        if 'jspa?id=' not in name[0]:
            print("Download Jira data for ", name[0])
            get_all_issues(name[0], name[1])
    
    return True, ""

