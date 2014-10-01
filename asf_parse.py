#!usr/bin/env python

from lxml import etree
import subprocess, re
import asf_db_client

def parse_svn_log(log, project_name):
    split_log = log.split('------------------------------------------------------------------------\nr')
    split_log = [l for l in split_log if not l.isspace() and l]
    
    for l in split_log:
        parse_svn_commit(l, project_name)
    
    return True

def parse_svn_commit(c, project_name):
    commit = {}
    commit['project'] = project_name
    
    log = c.splitlines()
    
    log = [l for l in log if not l.startswith('\'')]
    log = [l for l in log if not l.isspace() and l]
    
    rev_user_date = log[0]
    res = rev_user_date.split('|')
    
    # res should contain at least rev num, username, and commit date
    if len(res) < 3:
        return False
    
    commit['commit_id'] = res[0].strip()
    commit['username'] = res[1].strip()
    
    date_tmp = res[2].strip()
    date_tmp = date_tmp[:25]
    
    # for now, only record commits with dates in ISO 8601 with utc offset
    if (len(date_tmp) != 25):
        return False
    
    commit['date'] = date_tmp
    
    files = []
    i = 2
    if log[1] and 'Changed paths' in log[1]:
        while i < len(log)  and re.search("\s\s\s[A-Z]\s.*", log[i]):
            m_file = log[i].strip()
            file = {}
            file['commit_id'] = commit['commit_id']
            file['action'] = m_file[:1].strip()
            file['name'] = m_file[2:].strip()
            files.append(file)
            i = i + 1
    
    comment = ""
    for j in range(i, len(log)):
        comment = comment + log[j]
    
    commit['comment'] = comment
    
    valid_commit = asf_db_client.insert_commit(commit)
    
    if not valid_commit:
        return False

    for f in files:
        asf_db_client.insert_modified_file(f)
    
    return True
    
def parse_git_log(log, project_name):
    split_log = log.split('\'?||?')
    split_log = [l for l in split_log if not l.isspace() and l]
    
    for l in split_log:
        parse_git_commit(l, project_name)
        
    return True

def parse_git_commit(c, project_name):
    commit = {}
    commit['project'] = project_name
    
    log = c.splitlines()
    
    log = [l for l in log if not l.startswith('\'')]
    log = [l for l in log if l]
    
    hash_user_date = log[0]
    res = hash_user_date.split('|')
    commit['commit_id'] = res[0]
    commit['username'] = res[1]
    commit['date'] = res[2]

    comment = log[1]
    comment = comment[1:]
    if comment:
        commit['comment'] = comment

    valid_commit = False
    if "No Author" not in commit['username']:
        valid_commit = asf_db_client.insert_commit(commit)

    if not valid_commit:
        return False

    if len(log) > 2 and len(log) < 40:
        for x in range (2, len(log)):
            file = {}
            file['commit_id'] = res[0]
            file['action'] = log[x][:1]
            file['name'] = log[x][2:]
            asf_db_client.insert_modified_file(file)
    
    return True

def parse_doap(doap):
    tree = etree.parse('doap_files/' + doap)
    root = tree.getroot()
    
    project = {}
    
    for child in root:
        if child.tag == 'programming-languages' or child.tag == 'categories':
            value = []
            for grandchild in child:
                value.append(grandchild.text)
        else:
            value = child.text
        project[child.tag] = value
    
    if 'svn' in project['repository'] or 'subversion' in project['repository']:
        project['version_control'] = 'svn'
    elif 'git' in project['repository']:
        project['version_control'] = 'git'
    else:
        project['version_control'] = 'n/a'
        
    print("Inserting {0} into database.".format(project['name']))
    asf_db_client.insert_project(project)
    
    return True