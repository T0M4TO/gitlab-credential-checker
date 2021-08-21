#-*- coding: utf-8 -*-
import shutil
import os
import requests
import time
import datetime
from pytz import timezone
import docker
import json

# Read gitlab token from file
f = open("token","r")
token = f.readline().rstrip('\n')
f.close()

# Read slack webhook URI from file
f = open("webhook","r")
slack_url = f.readline().rstrip('\n')
f.close()

#docker setting
client = docker.from_env()

# List all gitlab project that you can access. Edit gitlab URI
url = "https://[your gitlab URI]/api/v4/projects"
headers = {
    'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'PRIVATE-TOKEN' : token
}
params={'simple':'true'}
res = requests.get(url, headers=headers, params=params).json()
# count projects
maximum = res[0]['id']

# check current date and time
nowadays = datetime.datetime.now(timezone('Asia/Seoul')).date()
if nowadays.weekday() == 0:
    nowadays = nowadays + datetime.timedelta(days=-3)
else:
    nowadays = nowadays + datetime.timedelta(days=-1)

# gitlab api only gives up to 20 results
# So repeat to get all results
cnt=20
while True:
    params = {'simple':'false','id_before':cnt,'id_after':cnt-20}
    res = requests.get(url, headers=headers, params=params).json()
    # End if cnt is bigger than number of projects
    if cnt-20>maximum:
        break

    # check the data
    for data in res:
        try:
            print(data['web_url'])
            print(data['id'])
            web_url = data['web_url']
            # Edit gitlat URI
            commit_url = "https://[your gitlab URI]/api/v4/projects/"+str(data['id'])+"/repository/commits"

            # Get commits of each project and use only latest commit
            res = requests.get(commit_url, headers=headers, params=params).json()[0]
            print(res['authored_date'])
            try:
                commit_time = res['authored_date'].split("T")[0]+" "+res['authored_date'].split("T")[1].split("+")[0]
                commit_time = datetime.datetime.strptime(commit_time, '%Y-%m-%d %H:%M:%S.%f')
                # If latest commit date depends on UTC, change it to KST
                if res['authored_date'].split("T")[1].split("+")[1].split(":")[0] != "09" :
                    timezone = 9-int(res['authored_date'].split("T")[1].split("+")[1].split(":")[0])
                    commit_time = commit_time + datetime.timedelta(hours=timezone)

            # If timezone is less than UTC
            except ValueError:
                commit_time = res['authored_date'].split("T")[0]+" "+res['authored_date'].split("T")[1].split("-")[0]
                commit_time = datetime.datetime.strptime(commit_time, '%Y-%m-%d %H:%M:%S.%f')
                # If latest commit date depends on UTC, change it to KST
                if res['authored_date'].split("T")[1].split("-")[1].split(":")[0] != "09" :
                    timezone = 9+int(res['authored_date'].split("T")[1].split("-")[1].split(":")[0])
                    commit_time = commit_time + datetime.timedelta(hours=timezone)

            print(nowadays)
            print(commit_time)

            # If latest commit is yesterday, check gitleaks
            if commit_time.date() >= nowadays :
                print("check commits")
                commit_id = res['id']

                command = '--leaks-exit-code=0 --repo-url="'+web_url+'" --access-token="'+token+'" --clone-path="[docker container clone path]" --report="[report file save path]" --commit="'+commit_id+'"'

                # make directory to get report from gitleaks container
                os.mkdir('[your host directory]')

                # gitleaks start
                client.containers.run('zricethezav/gitleaks', command, volumes={'[maked directory in host]': {'bind': '[bind directory in container]', 'mode': 'rw'}})

                # If gitleaks complete, continue task
                with open('[report file path in host]') as result_json:
                    json_datas = json.load(result_json)
                    try:
                        for json_data in json_datas:
                            leak_line = json_data['line']
                            leak_line_num = json_data['lineNumber']
                            leak_offender = json_data['offender']
                            leak_commitid = json_data['commit']
                            leak_repo = json_data['repo']
                            leak_repoURI = json_data['repoURL']
                            leak_URI = json_data['leakURL']
                            leak_rule = json_data['rule']
                            leak_author = json_data['author']
                            leak_email = json_data['email']
                            leak_date = json_data['date']

                            # make data for slack webhook.
                            slack_data = {"text":"*Credential이 포함된 Commit이 발견되었습니다.*\n> *시간* : "+str(leak_date)+"\n> *URI* : "+str(leak_URI)+"\n> * 라인* : "+str(leak_line)+"\n> *라인 번호* : "+str(leak_line_num)+"\n> *탐지 정책* : "+str(leak_rule)+"\n> *탐지 정책 상세* : "+str(leak_offender)+"\n> *Commit ID* : "+str(leak_commitid)+"\n> *프로젝트 명* : "+str(leak_repo)+"\n> *프로젝트 URI* : "+str(leak_repoURI)+"\n> *담당자* : "+str(leak_author)+"\n> *담당자 Email* : "+str(leak_email)}

                            requests.post(slack_url, json = slack_data)

                        # delete host directory to check next project
                        shutil.rmtree('[maked directory in host]')

                    # TypeError represents when commit do not have any leaks
                    except TypeError:
                        print('no leaks')
                        # delete host directory to check next project
                        shutil.rmtree('[maked directory in host]')
                        continue

        # IndexError represents when project do not have any data
        # KeyError represents when access token do not have enough permission to use project
        except (IndexError, KeyError):
            continue
    client.containers.prune()
    cnt = cnt+20
    time.sleep(1)
