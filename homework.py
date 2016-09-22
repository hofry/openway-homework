#!/usr/bin/python

import os, sys
import argparse
#import svn.remote
import sqlite3
import zipfile
import tempfile
import time
import shutil
import subprocess

def get_repos(file):
    return (line.rstrip() for line in open(file))

def svn_info(repo):
    p = subprocess.Popen("svn info "+repo, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, stderr = p.communicate()
    status = p.returncode
    if status != 0:
    	return False
    else:
        return True

def svn_co(repo, dst):
    repo_dir = dst+'/'+str(', '.join(repo.rstrip('/').split('/')[-1:]))
    os.chdir(dst)
    p = subprocess.Popen("svn co "+repo, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, stderr = p.communicate()
    status = p.returncode
    if status != 0:
    	return False
    else:
        return True

def mk_archive(tmp_dir, tmp_name, arch_dir):
    os.chdir(arch_dir)
    zipf = zipfile.ZipFile(tmp_name+'.zip', 'w', zipfile.ZIP_DEFLATED)
    zipdir(tmp_dir, zipf)
    zipf.close()
    

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

def rm_work_dir(tmp_dir):
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='input file', required=True)
    args = parser.parse_args()
    tmp_dir = tempfile.mkdtemp()
    tmp_name = str(', '.join(tmp_dir.rstrip('/').split('/')[-1:]))
    db_name = "transactions.db"
    arch_dir = os.getcwd()+'/archives'
    if not os.path.exists(arch_dir):
        os.mkdir(arch_dir)
    start = int(time.time())
    if os.path.isfile(args.file) and os.access(args.file, os.R_OK):
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        repos = get_repos(args.file)
        invalid_repos = []
        valid_repos = []
        if os.path.getsize(db_name) == 0:
            c.execute('''CREATE TABLE transactions
             (id INTEGER PRIMARY KEY NOT NULL,
              start INTEGER NOT NULL,
              end INTEGER NOT NULL,
              status VARCHAR(7) NOT NULL,
              content TEXT )''')
            conn.commit()
        for repo in repos:
            if svn_info(repo):
                if not svn_co(repo, tmp_dir):
                    print("ERROR Failed svn checkout")
                    invalid_repos.append(repo)
                else:
                    valid_repos.append(repo)
            else:
                print("ERROR: Failed svn info")
                invalid_repos.append(repo)
        if len(invalid_repos) == 0:
            mk_archive(tmp_dir, tmp_name, arch_dir)
            end = int(time.time())
            content = "ARCHIVE: "+tmp_name+".zip; CONTENT: "+str(valid_repos).strip('[]')
            #print content
            c.execute("INSERT INTO transactions VALUES (NULL, %i, %i, 'success', \"%s\")" % (start, end, content))
        else:
            end = int(time.time())
            content = "INVALID CONTENT: "+str(invalid_repos).strip('[]')
            #print content
            c.execute("INSERT INTO transactions VALUES (NULL, %i, %i, 'failed', \"%s\")" % (start, end, content))
        rm_work_dir(tmp_dir)
        conn.commit()
        conn.close()

    else:
        print("ERROR: File '%s' is missing or is not readable!" % args.file)

if __name__ == "__main__":
    main()
