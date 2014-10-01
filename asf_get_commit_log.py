#!usr/bin/env python

from datetime import datetime
import re, os, subprocess, dbm
import asf_parse

def get_svn_log(repo, project_name):
    """
    Download commit log from specified SVN repo.
    """
    
    # check if svn server is reachable
    try:
        svn_info = subprocess.check_output(["svn", "info", repo], stderr=subprocess.STDOUT).decode("utf-8")
    except:
        print("Failed to retrieve repo info for {0}.  Repository URL: {1}".format(project_name, repo))
        return False
    
    # get rev num of latest commit
    last_rev_num = re.search("Last Changed Rev:\s(.*)", svn_info).group(1)
    
    # check db for last commit rev num
    db = dbm.open('last_rev_num', 'c')
    range = ""
    if repo in db:
        stored_rev_num = db[repo].decode("utf-8")
        if last_rev_num == stored_rev_num:
            print("Commit log for {0} up to date.".format(project_name))
            return True
        else:
            range = "HEAD:" + stored_rev_num
    
    # get commit log
    try:
        if range:
            log_info = subprocess.check_output(["svn", "log", "-v", "-r", range, repo], stderr=subprocess.STDOUT).decode("utf-8")
        else:
            log_info = subprocess.check_output(["svn", "log", "-v", repo], stderr=subprocess.STDOUT).decode("utf-8")
    except:
        print("Failed to retrieve commit log for {0}.  Repository URL: {1}".format(project_name, repo))
        return False
        
    asf_parse.parse_svn_log(log_info, project_name)
    
    db[repo] = last_rev_num
    
    return True

def get_git_log(repo, project_name):
    """
    Download commit log from specified Git repo.
    """
    
    basename = os.path.basename(repo)
    m = re.search('([a-zA-Z0-9_\-]*)\.git', basename)
    shortname = m.group(1)

    cwd = os.getcwd()
    os.chdir('git_repos')
    
    # check what remote servers are already configured
    try:
        remote_info = subprocess.check_output(["git", "remote", "-v"], stderr=subprocess.STDOUT).decode("utf-8")
    except:
        print("Failed to retrieve remote info.")
        os.chdir(cwd)
        return False
        
    if not repo in remote_info:
        try:
            add_repo_info = subprocess.check_output(["git", "remote", "add", shortname, repo], stderr=subprocess.STDOUT).decode("utf-8")
        except:
            print("Failed to add remote repo {0}.".format(shortname))
            os.chdir(cwd)
            return False
    
    # pull down all missing data from remote project       
    try:
        fetch_info = subprocess.check_output(["git", "fetch", shortname], stderr=subprocess.STDOUT).decode("utf-8")
    except:
        print("Failed to fetch from remote repository {0}.".format(shortname))
        os.chdir(cwd)
        return False
    
    # checkout remote branch into working tree   
    try:   
        checkout_info = subprocess.check_output(["git", "checkout", "-f", "remotes/" + shortname + "/master"], stderr=subprocess.STDOUT).decode("utf-8")
    except:
        try:
            checkout_info = subprocess.check_output(["git", "checkout", "-f", "remotes/" + shortname + "/trunk"], stderr=subprocess.STDOUT).decode("utf-8")
        except:
            print("Failed to checkout {0} master branch".format(shortname))
            os.chdir(cwd)
            return False    
    
    # get hash of latest commit
    try:
        last_commit_hash = subprocess.check_output(["git", "log", "-1", "--pretty=format:%H"], stderr=subprocess.STDOUT).decode("utf-8")
    except:
        print("Failed to retrieve last commit hash for {0}.  Repository URL: {1}".format(project_name, repo))
        os.chdir(cwd)
        return False
    
    # check db for last commit hash
    db = dbm.open('last_commit_hash', 'c')
    range = ""
    if repo in db:
        stored_hash = db[repo].decode("utf-8")
        if last_commit_hash == stored_hash:
            print("Commit log for {0} up to date.".format(project_name))
            os.chdir(cwd)
            return True
        else:
            range = stored_hash + "..HEAD"
    
    # get commit log 
    try:
        if range:
            log_info = subprocess.check_output(["git", "log", range, "--pretty=format:'?||?%n%H|%an|%ci%n>%s%n'", "--name-status"], stderr=subprocess.STDOUT).decode("utf-8")
        else:
            log_info = subprocess.check_output(["git", "log", "--pretty=format:'?||?%n%H|%an|%ci%n>%s%n'", "--name-status"], stderr=subprocess.STDOUT).decode("utf-8")
    except:
        print("Failed to retrieve commit log for {0}.  Repository URL: {1}".format(project_name, repo))
        os.chdir(cwd)
        return False
    
    asf_parse.parse_git_log(log_info, project_name)
    
    db[repo] = last_commit_hash
    
    os.chdir(cwd)
    return True