# Gitlab_Credentials_Leak_Checker
Purpose of finding credentials exposed to gitlab projects

## Required Package
1. Docker
2. Python3

## How to use
1. Edit file named token. add line that contains your gitlab access token
2. Edit file named webhook. add line that contains your slack webhook URI
3. Edit start.py with referencee to comments (gitlab URI, host directory path, bind path etc)..
4. execute start.py using python3 (Need ROOT because of docker)

## Reference
- https://github.com/zricethezav/gitleaks

## Made By
- https://www.linkedin.com/in/hyeonjun-kwon-439563206/
