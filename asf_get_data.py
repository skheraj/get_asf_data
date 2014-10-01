#!usr/bin/env python

from lxml import etree
from urllib.request import urlopen, Request, HTTPError, URLError
import os, re, sys, stat, time, dbm, re, subprocess
import asf_parse, asf_get_commit_log, asf_db_client

DOAP_LIST_URL = 'http://svn.apache.org/repos/asf/infrastructure/site-tools/trunk/projects/files.xml'
DOAP_REPOS_DB = 'doap_files/doap_repos.db'
DOAP_REPOS_XML = 'xslt_files/doap_repos.xml'

############################################################################################################

def check_dependencies():
    """
    Verify the following requirements:
    (1) Python 3.4 or later
    (2) User has read/write access to cwd
    """
    # Check if machine is running Python 3.4 or later; if not, exit.
    if not re.search("^3.4.*", sys.version):
        return False, "ERROR: Program requires Python version 3.4 or later."
    
    # Check if user has write/read access to files in CWD; if not, exit.
    
    # Check if database exists with proper schema

    return True, "OK"

def generate_doap_file():
    """
    Download list of DOAP file urls from ASF.  Only download new list if local copy is older than copy on asf server.
    """
    
    file_name = os.path.basename(DOAP_LIST_URL)
    
    if os.path.isfile(file_name):
        res = get_helper(DOAP_LIST_URL, generate_if_modified_since(file_name))
    else:
        res = get_helper(DOAP_LIST_URL)
    
    if type(res) is HTTPError:
        if res.code == 304:
            print("Doap list not modified since last download.")
            return True, "OK"
        else:
            return False, "Failed to retrieve {0}.  Status code: {1}.".format(DOAP_LIST_URL, res.code)
    
    doap_xml = res.read().decode("utf-8")
    root = etree.fromstring(doap_xml)
    if root.tag != "doapFiles":
        return False, "Resource returned by DOAP_LIST_URL does not contain pointers to doap files"
    else:
        save_file(doap_xml, file_name)
        
    return True, "OK"
        
def generate_if_modified_since(file_path):
    """
    Given path to local file, return if-modified-since header using last modified date of file.
    """
    
    mtime = os.stat(file_path).st_mtime
    return {'IF-MODIFIED-SINCE':time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mtime))}

def get_helper(url, headers={}): 
    """
    Wrapper function for GET request.  Return file-like object representing HTTP response.
    """
    
    req = Request(url, headers=headers)

    try:
        response = urlopen(req)
    except HTTPError as e:
        return e
    except URLError as e:
        print("Failed to retrieve {0}.  Reason: {1}.".format(url, e.reason))
    except Exception as e:
        print("Failed to retrieve {0}.  Exception type: {1}.".format(url, type(e)))
    
    return response

def save_file(content, file_path, write_mode='w'):
    """
    Save file to disk; input: file content, output location and write mode.
    """
    
    if type(content) is bytes and write_mode == 'w':
        print("Content is bytes.")
        return False
    
    if type(content) is str and write_mode == 'wb':
        print("Content is str.")
        return False
    
    file = open(file_path, write_mode)
    file.write(content)
    file.close()
        
    return True

def generate_rdf_files():
    """
    Using the list of DOAP files retrieved by calling generate_doap_file(), download each individual DOAP file to disk.
    If doap file has not been modified since last download, do not download.
    """
    
    new_doaps = []
    if not os.path.exists('doap_files'):
        os.makedirs('doap_files')
    db = dbm.open('doap_files/doap', 'c')
    
    res, msg = generate_doap_repos_db()
    if not res:
        return False, msg, []
    
    tree = etree.parse('files.xml')
    root = tree.getroot()
    
    for location in root.iter('location'):
        if not location.text in db:
            res = get_helper(location.text)
        else:
            date = db[location.text].decode("utf-8").split('|')[0]
            res = get_helper(location.text, {'IF-MODIFIED-SINCE':date})
            
        if type(res) is HTTPError:
            if res.code == 304:
                continue
            else:
                return False, "Failed to retrieve {0}.  Status code: {1}.".format(location.text, res.code), []
        else:
            xml, file_name = transform_rdf(res.read())
            
            # If HTTP reponse does not have last-modified header, perform diff to check if file is modified
            if not res.info()['last-modified']:
                db[location.text] = res.info()['date'] + "|" + file_name 
                if os.path.isfile('doap_files/' + file_name):
                    with open('doap_files/' + file_name, "r") as file:
                        data = file.read()
                    if str(xml) == data:
                        continue
            else:
                db[location.text] = res.info()['last-modified'] + "|" + file_name
                            
            if not save_file(str(xml), 'doap_files/' + file_name):
                return False, "Failed to save file {0}.".format(file_name), []
            print("Saved new doap file from {0}".format(location.text))
            new_doaps.append(file_name)
                
    return True, "OK", new_doaps

def add_missing_repo(doap, file_name):
    """
    Add repo location if not included in DOAP file.
    """
    
    db = dbm.open('doap_files/doap_repos', 'c')
    repo = doap.find('repository')
    repo.text = db[file_name]
    
    return doap

def generate_doap_repos_db():
    """
    Create persistent map object on disk; object maps doap filename to repo url.
    Special entry db['last-modified'] returns date when doap_repos.xml was last modified.
    """
    
    # If doap_repos.xml does not exist, exit
    if not os.path.isfile(DOAP_REPOS_XML):
        return False, "Could not locate {0}.".format(DOAP_REPOS_XML)
    
    # Check if doaps_repos.xml has been updated since last time doap_repos.db was generated
    db = dbm.open('doap_files/doap_repos', 'c')
    last_modified = str(os.stat(DOAP_REPOS_XML).st_mtime)
    if 'last-modified' in db and db['last-modified'] == last_modified:
        return True, "OK"
    else:
        db['last-modified'] = last_modified
    
    tree = etree.parse(DOAP_REPOS_XML)
    root = tree.getroot()
    
    projects = ['last-modified']
    for project in root.iter('project'):
        key = project[0].text
        projects.append(key)
        val = project[1].text
        db[key] = val
    
    if not clean_doap_repos_db(projects):
        return False, "Failed to clean doap_repos.db file."
    
    return True, "OK"

def clean_doap_repos_db(projects):
    """
    Remove projects from doap_repos.db no longer listed in doap_repos.xml.
    """
    
    db = dbm.open('doap_files/doap_repos', 'c')
    
    for key in db.keys():
        key = key.decode("utf-8")
        if key not in projects:
            del db[key]
            print("Removed {0} entry from doap_repos.db".format(key))
    
    return True

def transform_rdf(rdf_content):
    """
    Transform doap file into XML containing only relevant elements.
    """
    
    xslt_file = etree.parse('xslt_files/project.xsl')
    rdf_file = etree.fromstring(rdf_content)
    transform = etree.XSLT(xslt_file)
    result_tree = transform(rdf_file)
    name = result_tree.find('name')
    file_name = name.text.replace(" ", "_") + '.rdf'
    
    db = dbm.open('doap_files/doap_repos', 'c')
    
    if file_name in db:
        result_tree = add_missing_repo(result_tree, file_name)
    
    repo = result_tree.find('repository')
    clean_repo_name = re.sub('git:http', 'http', repo.text)
    
    if "asf?" in clean_repo_name:
        m = re.search("(.*asf)\?p=(.*\.git).*", clean_repo_name)
        clean_repo_name = m.group(1) + "/" + m.group(2)
    
    repo.text = clean_repo_name
    
    return result_tree, file_name

def generate_commit_logs():
    """
    Read repository location from each doap file and use to download project commit log.
    """
    
    files = os.listdir('doap_files')
    
    if not os.path.exists('git_repos'):
            os.makedirs('git_repos')
            output = subprocess.check_output(["git", "init", "git_repos"], stderr=subprocess.STDOUT).decode("utf-8")
            if not "Initialized empty Git repository" in output:
                return False, "Failed to initialize Git repo."

    for f in files:
        if 'rdf' in str(f):
            tree = etree.parse('doap_files/' + f)
            root = tree.getroot()
            repo = root.find('repository').text
            project_name = root.find('name').text
            if 'svn' in repo:
                asf_get_commit_log.get_svn_log(repo, project_name)
            if '.git' in repo:
                asf_get_commit_log.get_git_log(repo, project_name)
    
    return True, "OK"


############################################################################################################

def main():
    res, msg = check_dependencies()
    
    if not res:
        print(msg)
        return
    
    res, msg = generate_doap_file()
    
    if not res:
        print(msg)
        return
    
    res, msg, updated_doap_list = generate_rdf_files()
    
    if not res:
        print(msg)
        return
    
    res = asf_db_client.open_connection()
    
    if not res:
        print("Failed to open database.")
        return
    
    for doap in updated_doap_list:
        asf_parse.parse_doap(doap)

    res, msg = generate_commit_logs()
    
    asf_db_client.close_connection()
    
    if not res:
        print(msg)
        return

if __name__ == '__main__':
    main()